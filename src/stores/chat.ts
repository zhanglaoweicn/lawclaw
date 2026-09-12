import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Session,
  Message,
  StepStartedEvent,
  StepFinishedEvent,
  AgUiEvent,
  RunFinishedEvent,
} from '../types/legal'
import { backend } from '../lib/backend'

/**
 * AG-UI Run Step（前端状态跟踪单元）
 * 每一次 run 都会产生一条 steps[] 序列：[1.推理 → 2.法规检索 → 3.推理 → 4.生成回复 ...]
 */
export interface RunStep {
  stepId: string
  stepIndex: number
  kind: StepStartedEvent['kind']        // 'tool' | 'think' | 'reply' | 'final'
  title: string
  description?: string
  status: 'running' | 'ok' | 'failed' | 'skipped'
  startedAt: string
  finishedAt?: string
  /** 对于 kind='tool'：绑定的工具调用 ID */
  toolCallId?: string
  /** 对于 kind='tool'：工具名称（如 "元典法规检索"） */
  toolName?: string
  /** 工具返回的摘要预览（AG-UI TOOL_CALL_RESULT.preview） */
  toolPreview?: string
}

/** Strip null/undefined values from an object before JSON serialization */
function stripNulls(obj: Record<string, unknown>): Record<string, unknown> {
  const clean: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(obj)) {
    if (v !== null && v !== undefined) {
      clean[k] = v
    }
  }
  return clean
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

function defaultSession(matterId?: string): Session {
  const now = new Date()
  return {
    id: generateId(),
    matterId,
    title: `新会话 ${now.toLocaleDateString('zh-CN')}`,
    createdAt: now,
    updatedAt: now,
    messageCount: 0,
  }
}

const SESSIONS_KEY = 'lawclaw_sessions'
const MESSAGES_PREFIX = 'lawclaw_msgs_'

function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    return raw ? JSON.parse(raw, (k, v) => k === 'createdAt' || k === 'updatedAt' ? new Date(v) : v) : []
  } catch {
    return []
  }
}

function saveSessions(sessions: Session[]) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
}

function loadMessages(sessionId: string): Message[] {
  try {
    const raw = localStorage.getItem(MESSAGES_PREFIX + sessionId)
    return raw ? JSON.parse(raw, (k, v) => k === 'timestamp' ? new Date(v) : v) : []
  } catch {
    return []
  }
}

function saveMessages(sessionId: string, messages: Message[]) {
  localStorage.setItem(MESSAGES_PREFIX + sessionId, JSON.stringify(messages))
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<Session[]>(loadSessions())
  const activeSessionId = ref<string | null>(null)
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const connected = ref(false)
  const pendingPrompt = ref<string | null>(null)
  /** 预填但 不自动发送 的输入（专家召唤等场景），与 pendingPrompt（自动发送）区分 */
  const pendingPrefill = ref<string | null>(null)
  const pendingSkill = ref<{ id: string; name: string; icon: string; prompt: string; rpcMethod?: string } | null>(null)
  const toolActivity = ref<{ name: string; status: 'running' | 'done'; args?: unknown } | null>(null)

  // ── AG-UI Run Steps（P1-2 进度条显示） ──
  /** 当前 run 的步骤列表；run 结束后保留最近一份用于 UI 查看 */
  const steps = ref<RunStep[]>([])
  /** 当前 runId（若有） */
  const currentRunId = ref<string | null>(null)
  /** 当前 run 所属会话（流式期间用户切走时，输出继续写入缓冲而非当前视图） */
  const runningSessionId = ref<string | null>(null)
  /** run 进行中被切走的会话 → 消息缓冲（切换回来时恢复，完成时落盘） */
  const sessionBuffers = new Map<string, Message[]>()
  /** 最近一次 run 是否以错误收场（驱动步骤面板的失败态展示） */
  const runFailed = ref(false)
  /** 当前 run 是否正在进行中 */
  const runInProgress = computed(() =>
    steps.value.some(s => s.status === 'running')
  )
  /** 已完成步骤数 */
  const completedSteps = computed(() =>
    steps.value.filter(s => s.status !== 'running').length
  )
  /** 总步骤数（run 进行中会持续增加，结束时锁定） */
  const totalSteps = computed(() => steps.value.length)
  /** Run 进度百分比（1-100） */
  const runProgressPercent = computed(() => {
    const total = steps.value.length
    if (total === 0) return 0
    const done = steps.value.filter(s => s.status === 'ok' || s.status === 'failed' || s.status === 'skipped').length
    const runningCount = steps.value.filter(s => s.status === 'running').length
    // running 步骤算 50%
    const weighted = done + runningCount * 0.5
    return Math.min(99, Math.max(0, Math.round((weighted / total) * 100)))
  })

  function _applyStepStarted(evt: StepStartedEvent) {
    // 去重（同一 stepId 只 push 一次）
    if (steps.value.find(s => s.stepId === evt.stepId)) return
    const step: RunStep = {
      stepId: evt.stepId,
      stepIndex: evt.stepIndex,
      kind: evt.kind,
      title: evt.title,
      description: evt.description || '',
      status: 'running',
      startedAt: evt.startedAt || '',
    }
    steps.value.push(step)
  }
  function _applyStepFinished(evt: StepFinishedEvent) {
    const s = steps.value.find(x => x.stepId === evt.stepId)
    if (!s) return
    s.status = evt.status as RunStep['status']
    s.finishedAt = evt.finishedAt
  }
  function _applyAgUiEvent(evt: AgUiEvent) {
    if (evt.type === 'STEP_STARTED') _applyStepStarted(evt)
    else if (evt.type === 'STEP_FINISHED') _applyStepFinished(evt)
    else if (evt.type === 'TOOL_CALL_START') {
      // 关联到最近的 running tool step（后端保证 TOOL_CALL_START 在 STEP_STARTED(kind='tool') 后立刻发）
      const lastToolStep = [...steps.value].reverse().find(s => s.kind === 'tool' && s.status === 'running')
      if (lastToolStep) {
        lastToolStep.toolCallId = evt.toolCallId
        lastToolStep.toolName = evt.toolName
      }
    }
    else if (evt.type === 'TOOL_CALL_RESULT') {
      const step = steps.value.find(s => s.toolCallId === evt.toolCallId)
      if (step) {
        step.toolPreview = evt.preview || ''
      }
    }
    else if (evt.type === 'RUN_STARTED') {
      currentRunId.value = evt.runId
      runFailed.value = false
    }
    else if (evt.type === 'RUN_ERROR') {
      // 官方规范：错误终止以 RUN_ERROR 结束（与 RUN_FINISHED 互斥，不会再收到 FINISHED）
      runFailed.value = true
      for (const s of steps.value) {
        if (s.status === 'running') s.status = 'failed'
      }
    }
    else if (evt.type === 'RUN_FINISHED') {
      // 收尾：确保所有 running step 都标记完成（错误终止走 RUN_ERROR 分支，不会到这里）
      const failed = false
      runFailed.value = failed
      for (const s of steps.value) {
        if (s.status === 'running') {
          s.status = failed ? 'failed' : 'ok'
        }
      }
    }
  }
  function _resetRunState() {
    steps.value = []
    currentRunId.value = null
  }

  // Per-request abort flag — set by abortCurrentMessage, checked in .then() and callbacks
  let currentAbortFlag: { value: boolean } | null = null

  // ── Abort support ──
  let abortRequested = false

  function setPendingPrompt(text: string) {
    pendingPrompt.value = text
  }

  function consumePendingPrompt(): string | null {
    const val = pendingPrompt.value
    pendingPrompt.value = null
    return val
  }

  function setPendingPrefill(text: string) {
    pendingPrefill.value = text
  }

  function consumePendingPrefill(): string | null {
    const val = pendingPrefill.value
    pendingPrefill.value = null
    return val
  }

  function setPendingSkill(s: { id: string; name: string; icon: string; prompt: string; rpcMethod?: string }) {
    pendingSkill.value = s
  }

  function consumePendingSkill(): { id: string; name: string; icon: string; prompt: string; rpcMethod?: string } | null {
    const val = pendingSkill.value
    pendingSkill.value = null
    return val
  }

  const activeSession = computed(() => sessions.value.find(s => s.id === activeSessionId.value) || null)

  const sessionsForMatter = computed(() => (matterId: string) =>
    sessions.value.filter(s => s.matterId === matterId)
  )

  const recentSessions = computed(() =>
    [...sessions.value].sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime()).slice(0, 10)
  )

  function ensureFirstSession() {
    if (sessions.value.length === 0) {
      const s = defaultSession()
      sessions.value.push(s)
      saveSessions(sessions.value)
    }
    if (!activeSessionId.value) {
      activeSessionId.value = sessions.value[0].id
      messages.value = loadMessages(activeSessionId.value)
    }
  }

  function switchSession(id: string) {
    if (activeSessionId.value) {
      saveMessages(activeSessionId.value, messages.value)
      // run 进行中切走：保留内存缓冲，后续 delta 继续写入该缓冲，run 完成时落盘
      if (loading.value && runningSessionId.value === activeSessionId.value) {
        sessionBuffers.set(activeSessionId.value, messages.value)
      }
    }
    activeSessionId.value = id
    // 切回正在流式输出的会话时恢复缓冲（否则读到的是落盘前的旧状态）
    const buffered = sessionBuffers.get(id)
    messages.value = buffered ? buffered : loadMessages(id)
  }

  function newSession(matterId?: string) {
    const s = defaultSession(matterId)
    sessions.value.unshift(s)
    saveSessions(sessions.value)
    switchSession(s.id)
  }

  function newSessionWithExpert(role: { id: string; name: string; systemPrompt: string; samplePrompt: string }, matterId?: string) {
    const s = defaultSession(matterId)
    s.title = role.name
    s.systemPrompt = role.systemPrompt
    s.expertRoleId = role.id
    sessions.value.unshift(s)
    saveSessions(sessions.value)
    switchSession(s.id)
  }

  function clearExpertRole() {
    const s = activeSession.value
    if (!s) return
    s.systemPrompt = undefined
    s.expertRoleId = undefined
    saveSessions(sessions.value)
  }

  function setExpertRole(role: { id: string; name: string; systemPrompt: string }) {
    const s = activeSession.value
    if (!s) return
    s.title = role.name
    s.systemPrompt = role.systemPrompt
    s.expertRoleId = role.id
    saveSessions(sessions.value)
  }

  function deleteSession(id: string) {
    const idx = sessions.value.findIndex(s => s.id === id)
    if (idx === -1) return
    sessions.value.splice(idx, 1)
    localStorage.removeItem(MESSAGES_PREFIX + id)
    saveSessions(sessions.value)
    if (id === activeSessionId.value) {
      if (sessions.value.length > 0) {
        switchSession(sessions.value[0].id)
      } else {
        // Auto-create a new session when the last one is deleted
        const s = defaultSession()
        sessions.value.push(s)
        saveSessions(sessions.value)
        switchSession(s.id)
      }
    }
  }

  function renameSession(id: string, title: string) {
    const s = sessions.value.find(s => s.id === id)
    if (s) {
      s.title = title
      s.updatedAt = new Date()
      saveSessions(sessions.value)
    }
  }

  function linkSessionToMatter(sessionId: string, matterId: string) {
    const s = sessions.value.find(s => s.id === sessionId)
    if (s) {
      s.matterId = matterId
      saveSessions(sessions.value)
    }
  }

  function unlinkMatter(matterId: string) {
    for (const s of sessions.value) {
      if (s.matterId === matterId) {
        s.matterId = undefined
      }
    }
    saveSessions(sessions.value)
  }

  function findOrCreateSessionForMatter(matterId: string): Session {
    const existing = sessions.value
      .filter(s => s.matterId === matterId)
      .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime())
    if (existing.length > 0) {
      switchSession(existing[0].id)
      return existing[0]
    }
    const s = defaultSession(matterId)
    sessions.value.unshift(s)
    saveSessions(sessions.value)
    switchSession(s.id)
    return s
  }

  backend.onStatusChange = (v) => { connected.value = v }

  async function connectBackend() {
    if (backend.isConnected()) { connected.value = true; return }
    try {
      await backend.connect()
      connected.value = true
    } catch {
      console.warn('后端未就绪，将在后台自动重试')
    }
  }

  function saveCurrentMessages() {
    if (activeSessionId.value) {
      saveMessages(activeSessionId.value, messages.value)
    }
  }

  async function abortCurrentMessage(apiKey?: string, baseUrl?: string, model?: string) {
    abortRequested = true
    // P0-2: 真中止 —— 调用后端 abort RPC，触发 threading.Event + interrupt
    try {
      await backend.abort(apiKey, baseUrl, model)
    } catch {
      // 即使 RPC 失败也要更新 UI
    }
    loading.value = false
    // 中止目标按 run 归属会话定位（用户可能已切走）
    const runId = runningSessionId.value
    const target = (runId && activeSessionId.value !== runId)
      ? sessionBuffers.get(runId)
      : messages.value
    if (target) {
      const lastMsg = target[target.length - 1]
      if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content === '') {
        lastMsg.content = '⏸️ 已中止'
      }
    }
    if (runId) {
      saveMessages(runId, (runId === activeSessionId.value) ? messages.value : (sessionBuffers.get(runId) || loadMessages(runId)))
    }
  }

  function editMessage(messageId: string, newContent: string) {
    const idx = messages.value.findIndex(m => m.id === messageId)
    if (idx === -1) return

    // If editing an assistant message, just update content
    if (messages.value[idx].role === 'assistant') {
      messages.value[idx].content = newContent
      messages.value[idx].timestamp = new Date()
      if (activeSessionId.value) {
        saveMessages(activeSessionId.value, messages.value)
      }
      return
    }

    // If editing a user message, truncate all messages after it and add content
    messages.value.splice(idx + 1, messages.value.length - (idx + 1))
    if (messages.value[idx]) {
      messages.value[idx].content = newContent
      messages.value[idx].timestamp = new Date()
    }

    // Update session messageCount
    const session = activeSession.value
    if (session) {
      session.messageCount = messages.value.filter(m => m.role === 'user').length
      session.updatedAt = new Date()
      saveSessions(sessions.value)
    }

    saveMessages(activeSessionId.value!, messages.value)
  }

  async function sendMessage(text: string, apiKey?: string, baseUrl?: string, model?: string, skillId?: string, files?: { name: string; data: string }[]) {
    if (!text.trim() || loading.value) return

    // Reset abort flag
    abortRequested = false
    // Reset AG-UI run state (steps / progress bar)
    _resetRunState()

    const userMsg: Message = {
      id: generateId(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    }
    messages.value.push(userMsg)
    loading.value = true

    // 记录本次 run 的归属会话：流式期间用户切走时，输出写入缓冲而非当前视图
    const runSessionId = activeSessionId.value ?? 'default'
    runningSessionId.value = runSessionId
    /** run 的输出目标：当前视图（未切走）或切走前的内存缓冲 */
    function runMessages(): Message[] {
      if (activeSessionId.value === runSessionId) return messages.value
      let buf = sessionBuffers.get(runSessionId)
      if (!buf) {
        buf = loadMessages(runSessionId)
        sessionBuffers.set(runSessionId, buf)
      }
      return buf
    }

    let session = activeSession.value
    if (session && session.messageCount === 0) {
      const title = text.length > 20 ? text.slice(0, 20) + '...' : text
      renameSession(session.id, title)
    }

    // ── Assistant message ID (placeholder created on first delta) ──
    let assistantMsgId: string | null = null
    let assistantMsgCreated = false

    function ensureAssistantMsg() {
      if (assistantMsgCreated) return
      assistantMsgCreated = true
      assistantMsgId = generateId()
      const msg: Message = {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      }
      runMessages().push(msg)
    }

    try {
      const params: Record<string, unknown> = {}
      params.api_key = apiKey || ''
      params.base_url = baseUrl || ''
      params.model = model || ''
      // AG-UI threadId（官方必填字段，LawClaw 语义 = 会话 ID）
      params.thread_id = activeSessionId.value || 'default'

      // ── Inject expert system prompt if session has one ──
      const curSession = activeSession.value
      if (curSession?.systemPrompt) {
        params.system_prompt = curSession.systemPrompt
      }

      // ── P0-3: 注入律师执业画像（让后端构建个性化 system_prompt） ──
      try {
        const { useSetupStore } = await import('./setup')
        const setupStore = useSetupStore()
        if (setupStore.profile) {
          params.profile = {
            name: setupStore.profile.name,
            firm: setupStore.profile.firm,
            title: setupStore.profile.title,
            practiceAreas: setupStore.profile.practiceAreas,
            teamSize: setupStore.profile.teamSize,
            yearsOfPractice: setupStore.profile.yearsOfPractice,
          }
        }
      } catch {
        // setup store 尚未初始化，跳过画像注入
      }

      // ── 案件知识库：该案件已解析文件的全文（后端 BM25 按问题选段注入） ──
      try {
        const { useMatterStore: useMS2 } = await import('./matter')
        const matterStore2 = useMS2()
        const matterId = (curSession?.matterId || matterStore2.activeMatterId || '') as string
        if (matterId) {
          const { useFileStore } = await import('./fileStore')
          const fs = useFileStore()
          const docs = fs.files
            .filter(f => f.matterId === matterId && f.extractedText)
            .slice(0, 8)
            .map(f => ({ name: f.name, text: (f.extractedText as string).slice(0, 30000) }))
          if (docs.length) {
            params.matter_documents = docs
            params.matter_id = matterId
          }
        }
      } catch {
        // 文件库未就绪，跳过知识库注入
      }

      // ── 经验记忆：跨案件描述 + 本案决策/里程碑事件（后端 BM25 排序召回） ──
      try {
        const { useMatterStore: useMS } = await import('./matter')
        const matterStore = useMS()
        const expItems: Array<Record<string, unknown>> = []
        for (const m of matterStore.matters) {
          const text = [m.description, m.caseCause, m.stage].filter(Boolean).join('；')
          if (text && text.length > 8) {
            expItems.push({
              id: m.id, matterTitle: m.client || m.title,
              title: m.title, text, type: 'matter',
            })
          }
        }
        const { useTimelineStore } = await import('./timeline')
        const tl = useTimelineStore()
        // 无条件尝试全量加载（内部有幂等守卫）——进过某案详情后 events 只剩单案，
        // 跳过会导致跨案件经验召回静默退化
        await tl.loadAllEvents().catch(() => undefined)
        for (const e of tl.events) {
          if (e.type === 'decision' || e.type === 'milestone') {
            expItems.push({
              id: e.id,
              matterTitle: matterStore.matters.find(m => m.id === e.matterId)?.title || '本案',
              title: e.title, text: e.description || '', type: e.type,
              date: e.createdAt instanceof Date ? e.createdAt.toISOString() : String(e.createdAt),
            })
          }
        }
        if (expItems.length) params.experience_items = expItems.slice(0, 400)
      } catch {
        // 时间轴未就绪，跳过经验召回
      }

      // ── P0-1: 注入对话历史（让 agent 具备多轮记忆） ──
      // 取当前 messages（不含刚 push 的用户消息），转为 OpenAI 格式
      // 后端会自动截断到最近 20 轮
      const historyForBackend = messages.value
        .slice(0, -1)  // 排除刚 push 的用户消息
        .filter(m => m.content && m.content.trim() && m.content !== '⏸️ 已中止')
        .map(m => ({
          role: m.role === 'user' ? 'user' : 'assistant',
          content: m.content,
        }))
      if (historyForBackend.length > 0) {
        params.conversation_history = historyForBackend
      }

      // ── P1-2: 注入案件上下文（深度增强版） ──
      if (curSession?.matterId) {
        try {
          const { useMatterStore } = await import('./matter')
          const matterStore = useMatterStore()
          const matter = matterStore.matters.find(m => m.id === curSession.matterId)
          if (matter) {
            const ctx: Record<string, string> = {}
            if (matter.title) ctx.title = matter.title
            if (matter.stage) ctx.stage = matter.stage
            if (matter.caseNumber) ctx.caseNumber = matter.caseNumber
            if (matter.client) ctx.client = matter.client
            if (matter.counterparty) ctx.counterparty = matter.counterparty
            if (matter.courtName) ctx.courtName = matter.courtName
            if (matter.practiceArea) ctx.practiceArea = matter.practiceArea
            if (matter.description) ctx.description = matter.description
            if (matter.deadline) ctx.deadline = matter.deadline
            if (matter.courtDate) ctx.courtDate = matter.courtDate
            // P1-2 扩展字段
            if (matter.caseCause) ctx.caseCause = matter.caseCause
            if (matter.procedureStage) ctx.procedureStage = matter.procedureStage
            if (matter.claimAmount !== undefined) ctx.claimAmount = String(matter.claimAmount)
            if (matter.clientRole) ctx.clientRole = matter.clientRole
            if (matter.opposingCounsel) ctx.opposingCounsel = matter.opposingCounsel
            if (matter.riskLevel) ctx.riskLevel = matter.riskLevel
            // 活跃期限摘要（只传最近 3 个，避免 token 膨胀）
            if (matter.deadlines && matter.deadlines.length > 0) {
              const activeDls = matter.deadlines
                .filter(d => !d.completed && !d.supersededAt)
                .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
                .slice(0, 3)
              if (activeDls.length > 0) {
                ctx.activeDeadlines = activeDls
                  .map(d => `${d.type}:${d.date}`)
                  .join('|')
              }
            }
            if (Object.keys(ctx).length > 0) {
              params.matter_context = ctx
            }
          }
        } catch {
          // Silent fail — context injection is best-effort
        }
      }

      // ── Inject skill_id if user activated a specific skill ──
      if (skillId) {
        params.skill_id = skillId
      }

      // ── Inject files if attached ──
      if (files && files.length > 0) {
        params.files = files.map(f => ({ name: f.name, data: f.data, type: '' }))
      }

      // Streaming chat — create message on first delta, append thereafter
      // Remove any null/undefined values before sending (prevents Python NoneType errors)
      const cleanParams = stripNulls(params)
      // Per-request abort flag — prevents .then() from overwriting after abort
      const myAbortFlag = { value: false }
      currentAbortFlag = myAbortFlag

      // 当前 agent 的配置（用于 abort RPC）
      const abortApiKey = apiKey || ''
      const abortBaseUrl = baseUrl || ''
      const abortModel = model || ''

      await backend.chatStream(
        text.trim(),
        cleanParams,
        {
          onAgUiEvent: (evt: AgUiEvent) => {
            if (myAbortFlag.value) return
            _applyAgUiEvent(evt)
          },
          onStepStarted: (step) => {
            if (myAbortFlag.value) return
            _applyStepStarted(step)
          },
          onStepFinished: (step) => {
            if (myAbortFlag.value) return
            _applyStepFinished(step)
          },
          onRunFinished: (evt) => {
            if (myAbortFlag.value) return
            _applyAgUiEvent(evt)
          },
          onDelta: (chunk: string) => {
            if (myAbortFlag.value) return
            ensureAssistantMsg()
            const msgs = runMessages()
            const idx = msgs.findIndex(m => m.id === assistantMsgId)
            if (idx !== -1) {
              msgs[idx] = { ...msgs[idx], content: msgs[idx].content + chunk }
            }
          },
          onToolStart: (name: string, args: unknown) => {
            if (myAbortFlag.value) return
            toolActivity.value = { name, status: 'running', args }
          },
          onToolComplete: (name: string, _result: unknown) => {
            if (myAbortFlag.value) return
            toolActivity.value = { name, status: 'done' }
            setTimeout(() => {
              if (toolActivity.value?.name === name) {
                toolActivity.value = null
              }
            }, 1500)
          },
          onThinking: (text: string) => {
            if (myAbortFlag.value) return
            ensureAssistantMsg()
            const msgs = runMessages()
            const idx = msgs.findIndex(m => m.id === assistantMsgId)
            if (idx !== -1) {
              const existing = msgs[idx].reasoning || ''
              msgs[idx] = { ...msgs[idx], reasoning: existing + text }
            }
          },
        },
      ).then((result) => {
        if (myAbortFlag.value) return
        if (!assistantMsgCreated) {
          ensureAssistantMsg()
        }
        toolActivity.value = null
        const msgs = runMessages()
        const idx = msgs.findIndex(m => m.id === assistantMsgId)
        if (idx !== -1) {
          msgs[idx] = {
            ...msgs[idx],
            content: result.response || msgs[idx].content,
            citations: result.citations as any,
            error: (result as { error?: boolean }).error === true,
            contextStats: (result as { context_stats?: Message['contextStats'] }).context_stats,
          }
        }
      })
    } catch (e) {
      console.error('sendMessage error:', e)
      toolActivity.value = null
      ensureAssistantMsg()
      const msgs = runMessages()
      const idx = msgs.findIndex(m => m.id === assistantMsgId)
      if (idx !== -1) {
        const errMsg = e instanceof Error ? e.message : '未知错误'
        msgs[idx] = {
          ...msgs[idx],
          content: (errMsg === 'Backend not connected' || errMsg.includes('启动中'))
            ? '后端引擎尚未就绪（启动通常需要 10–30 秒）。请稍候重试；若持续失败，请查看安装目录下的 launcher.log。'
            : `请求失败：${errMsg}`,
          error: true,
        }
      }
    }

    loading.value = false
    runningSessionId.value = null
    const runMsgs = runMessages()
    if (session) {
      session.messageCount = runMsgs.filter(m => m.role === 'user').length
      session.updatedAt = new Date()
      saveSessions(sessions.value)
    }
    if (activeSessionId.value === runSessionId) {
      saveMessages(runSessionId, messages.value)
    } else {
      // 会话已被切走：把缓冲落盘到归属会话，并清理缓冲
      const buf = sessionBuffers.get(runSessionId)
      if (buf) saveMessages(runSessionId, buf)
      sessionBuffers.delete(runSessionId)
    }
  }

  // Auto-save messages when user leaves the page (prevents data loss when closing tab)
  if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', () => {
      if (activeSessionId.value && messages.value.length > 0) {
        saveMessages(activeSessionId.value, messages.value)
      }
    })
  }

  return {
    sessions, activeSessionId, messages, loading, connected, pendingPrompt,
    toolActivity, runningSessionId,
    // ── AG-UI 协议新状态（P0/P1） ──
    steps, currentRunId, runInProgress, runFailed, completedSteps, totalSteps, runProgressPercent,
    activeSession, sessionsForMatter, recentSessions,
    ensureFirstSession,
    switchSession, newSession, newSessionWithExpert, setExpertRole, clearExpertRole, deleteSession, renameSession, linkSessionToMatter, findOrCreateSessionForMatter, unlinkMatter,
    connectBackend, sendMessage, saveCurrentMessages,
    setPendingPrompt, consumePendingPrompt, setPendingSkill, consumePendingSkill,
    setPendingPrefill, consumePendingPrefill,
    abortCurrentMessage, abortRequested, editMessage,
  }
})
