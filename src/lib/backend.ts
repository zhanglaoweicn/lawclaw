import type {
  ChatStreamCallbacks,
  AgUiEvent,
  StepStartedEvent,
  StepFinishedEvent,
  RunFinishedEvent,
} from '../types/legal'

type WireMessage = {
  jsonrpc?: '2.0'
  result?: unknown
  error?: { code: number; message: string }
  id?: number
  // ── 旧 legacy 流式事件（后端仍会双发，旧前端消费） ──
  type?: string
  data?: unknown
  // ── 新 AG-UI 事件包装（后端发送 event='agui' + payload） ──
  event?: string
  payload?: unknown
  // ── 握手信息 ──
  model?: string
  ag_ui_version?: string
}

let requestId = 0

export class BackendClient {
  private ws: WebSocket | null = null
  private pending = new Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }>()
  private url: string
  connected = false
  private pendingConnect: Promise<void> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private closedByUser = false
  onStatusChange?: (connected: boolean) => void

  /** 服务端是否支持 AG-UI 协议（根据握手消息 ag_ui_version 判定） */
  serverAgUiVersion: string | null = null

  /** Registered streaming callback — set per chatStream call */
  private streamCb: ChatStreamCallbacks | null = null

  /** Run / Step 状态跟踪（供内部转换，避免重复发 legacy） */
  private currentRunId: string | null = null
  public get runId(): string | null {
    return this.currentRunId
  }

  constructor(url = 'ws://127.0.0.1:9876') {
    this.url = url
  }

  isConnected(): boolean {
    return this.connected
  }

  private setConnected(v: boolean) {
    if (this.connected !== v) {
      this.connected = v
      this.onStatusChange?.(v)
    }
  }

  connect(): Promise<void> {
    if (this.pendingConnect) return this.pendingConnect
    if (this.ws) { this.ws.onclose = null; this.ws.close() }
    this.pendingConnect = new Promise<void>((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)
      } catch (e) {
        this.pendingConnect = null
        reject(e)
        return
      }
      this.ws.onopen = () => {
        this.setConnected(true)
        this.pendingConnect = null
        resolve()
      }
      this.ws.onmessage = (event) => {
        let data: WireMessage
        try {
          data = JSON.parse(event.data) as WireMessage
        } catch {
          // ignore non-JSON frames
          return
        }

        // ── 握手 ready 消息（含协议版本号） ──
        if (data.event === 'ready') {
          this.serverAgUiVersion = (data.ag_ui_version as string) || null
          return
        }

        // ── AG-UI 事件（P0/P1 新协议） ──
        if (data.event === 'agui' && data.payload) {
          const cb = this.streamCb
          const evt = data.payload as AgUiEvent
          // 先派发原始事件钩子（新代码优先）
          cb?.onAgUiEvent?.(evt)
          // 再派发分类钩子
          if (evt.type === 'RUN_STARTED') {
            this.currentRunId = evt.runId
            cb?.onRunStarted?.(evt.runId)
          } else if (evt.type === 'STEP_STARTED') {
            cb?.onStepStarted?.(evt as StepStartedEvent)
          } else if (evt.type === 'STEP_FINISHED') {
            cb?.onStepFinished?.(evt as StepFinishedEvent)
          } else if (evt.type === 'RUN_FINISHED') {
            cb?.onRunFinished?.(evt as RunFinishedEvent)
          }
          // ── AG-UI → legacy 兼容性自动转换 ──
          // 注意：后端也会双发 legacy 事件，这里再加会重复。
          // 所以 AG-UI → legacy 转换仅在 handshake 显示"没有 legacy 事件"时启用。
          // 目前策略：不做重复转换，只保留"没有 legacy 事件兜底"
          // （后端通过 EventEmitter 保证 legacy 事件会在 AG-UI 事件后立刻双发）
          return
        }

        // ── Legacy 流式事件（无 jsonrpc id，有 type 字段） ──
        if (data.id === undefined && data.type) {
          const cb = this.streamCb
          if (!cb) return
          if (data.type === 'delta' && cb.onDelta) {
            cb.onDelta(data.data as string)
          } else if (data.type === 'tool_start' && cb.onToolStart) {
            const d = data.data as { name: string; args: unknown }
            cb.onToolStart(d.name, d.args)
          } else if (data.type === 'tool_complete' && cb.onToolComplete) {
            const d = data.data as { name: string; result: unknown }
            cb.onToolComplete(d.name, d.result)
          } else if (data.type === 'thinking' && cb.onThinking) {
            cb.onThinking(data.data as string)
          }
          return
        }

        // ── JSON-RPC response ──
        if (data.id !== undefined) {
          const pending = this.pending.get(data.id)
          if (pending) {
            this.pending.delete(data.id)
            if (data.error) {
              pending.reject(new Error(data.error.message))
            } else {
              pending.resolve(data.result)
            }
          }
        }
      }
      this.ws.onerror = () => {
        this.setConnected(false)
        this.pendingConnect = null
        reject(new Error('WebSocket connection failed'))
      }
      this.ws.onclose = () => {
        this.setConnected(false)
        this.pendingConnect = null
        for (const [, p] of this.pending) p.reject(new Error('Connection closed'))
        this.pending.clear()
        this.scheduleReconnect()
      }
    })
    return this.pendingConnect
  }

  private scheduleReconnect() {
    if (this.closedByUser || this.pendingConnect) return
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(() => {})
    }, 3000)
  }

  async call<T = unknown>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    if (!this.connected) {
      await this.waitForConnect()
    }
    const id = ++requestId
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve: resolve as (v: unknown) => void, reject })
      this.ws!.send(JSON.stringify({ jsonrpc: '2.0', id, method, params }))
    }) as Promise<T>
  }

  /**
   * Streaming chat — 收到消息后会派发：
   * ① onAgUiEvent(evt)  —  新 AG-UI 协议，所有 16 类事件
   * ② onRunStarted / onStepStarted / onStepFinished / onRunFinished  —  分类简化钩子
   * ③ onDelta / onToolStart / onToolComplete / onThinking  —  向后兼容（旧逻辑）
   */
  async chatStream(
    message: string,
    params: Record<string, unknown>,
    callbacks: ChatStreamCallbacks,
  ): Promise<{ response: string; citations?: unknown[] }> {
    this.streamCb = callbacks
    this.currentRunId = null
    try {
      const result = await this.call<{ response: string; citations?: unknown[] }>('chat', {
        message,
        ...params,
      })
      return result
    } finally {
      this.streamCb = null
    }
  }

  private async waitForConnect(): Promise<void> {
    if (this.connected) return
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      this.connect().catch(() => {})
    }
    for (let i = 0; i < 50; i++) {
      await new Promise(r => setTimeout(r, 200))
      if (this.connected) return
    }
    throw new Error('后端未连接，请确保 LawClaw 引擎已启动并配置了 API Key。')
  }

  async initialize(): Promise<{ status: string; version: string; name: string }> {
    return this.call('initialize')
  }

  /** 真实调用一次最小补全验证 API 可用性（比 initialize 的"已配置"检查可靠） */
  async testLlm(apiKey?: string, baseUrl?: string, model?: string): Promise<{
    ok: boolean; model: string; latency_ms?: number; message?: string; sample?: string
  }> {
    return this.call('test_llm', { api_key: apiKey, base_url: baseUrl, model })
  }

  /** 文档抽取适配层：PDF/DOCX/XLSX → 全文文本（base64 数据入，文本出） */
  async parseDocument(filename: string, dataBase64: string): Promise<{
    ok: boolean; text?: string; extractor?: string; chars?: number; error?: string
  }> {
    return this.call('parse_document', { filename, data_base64: dataBase64 })
  }

  /** Markdown 文书 → Word (.docx)，返回 base64 文件数据 */
  async exportDocx(title: string, markdown: string, matterTitle?: string): Promise<{
    ok: boolean; filename?: string; data?: string; error?: string
  }> {
    return this.call('export_docx', { title, markdown, matter_title: matterTitle || '' })
  }

  /** Legacy non-streaming chat — kept for backward compat */
  async chat(message: string): Promise<{ response: string }> {
    return this.call('chat', { message })
  }

  async legalSearch(query: string, searchType = 'law'): Promise<{ results: unknown[] }> {
    return this.call('legal_search', { query, search_type: searchType })
  }

  /** 验证法条是否现行有效 */
  async verifyCitation(law: string, article = ''): Promise<{
    valid: boolean | null
    deprecated?: boolean
    bbbs?: string
    law_name?: string
    status?: string
    replaced_by?: string
    effective_until?: string
    publish_date?: string
    department?: string
    note?: string
    source?: string
    error?: string
  }> {
    return this.call('verify_citation', { law, article })
  }

  /** 根据案件阶段获取推荐技能 */
  async recommendSkillsForStage(stage: string): Promise<{
    stage: string; recommended_skills: Array<{ id: string; name: string; icon: string; reason: string }>
  }> {
    return this.call('recommend_skills_for_stage', { stage })
  }

  /** 计算诉讼时效 */
  async calcLimitationPeriod(caseType: string, eventDate: string): Promise<{
    deadline?: string; days_remaining?: number; status?: string; law_basis?: string; note?: string; error?: string
  }> {
    return this.call('calc_limitation_period', { case_type: caseType, event_date: eventDate })
  }

  /** 真中止当前 LLM 调用（P0-2） */
  async abort(apiKey?: string, baseUrl?: string, model?: string): Promise<{ status: string }> {
    return this.call('abort', { api_key: apiKey || '', base_url: baseUrl || '', model: model || '' })
  }

  /** 值守助手：同步案件摘要（供 cron 晨报扫描） */
  async watchdogSync(matters: Array<Record<string, unknown>>): Promise<{ synced: number }> {
    return this.call('watchdog_sync', { matters })
  }

  /** 值守助手：即时扫描状态 */
  async watchdogStatus(): Promise<{
    syncedAt: string | null; matters: number
    alerts: Array<{ kind: string; matter: string; detail: string; date: string; days: number }>
    alertText: string
  }> {
    return this.call('watchdog_status', {})
  }

  /** 值守助手：最近晨报/周报 */
  async watchdogBriefing(job = 'lawclaw-morning-briefing'): Promise<{ found: boolean; output?: string; status?: string; at?: string; error?: string }> {
    return this.call('watchdog_briefing', { job })
  }

  /** 值守助手：立即触发晨报生成 */
  async watchdogRunNow(job = 'lawclaw-morning-briefing'): Promise<{ triggered: boolean; job?: string; error?: string }> {
    return this.call('watchdog_run_now', { job })
  }

  /** 文书细节校对（M1-M8 规则 + 法条时效验证） */
  async reviewDocument(text: string, checkCitations = true): Promise<{
    issues: Array<{ module: string; severity: string; message: string; suggestion: string; line: number; excerpt: string }>
    stats: { chars: number; lines: number; by_module: Record<string, number>; by_severity: Record<string, number> }
  }> {
    return this.call('review_document', { text, check_citations: checkCitations })
  }

  /** 国家法律法规数据库：官方法规文件下载签名 URL（约 1 小时有效） */
  async npcDocxUrl(bbbs: string, format: string = 'docx'): Promise<{ url: string }> {
    return this.call('npc_law_docx_url', { bbbs, format })
  }

  /** 期限智能引擎：考虑节假日顺延（P1-3） */
  async calcDeadline(startDate: string, days: number, deadlineType: string = 'custom', skipHolidays = true): Promise<{
    deadline?: string; original_deadline?: string; deferred?: boolean; deferred_reason?: string
    start_date?: string; days?: number; deadline_type?: string
    days_remaining?: number; status?: string; law_basis?: string; error?: string
  }> {
    return this.call('calc_deadline', {
      start_date: startDate, days, deadline_type: deadlineType, skip_holidays: skipHolidays
    })
  }

  disconnect() {
    this.closedByUser = true
    this.setConnected(false)
    this.streamCb = null
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    if (this.pendingConnect) { this.pendingConnect = null }
    if (this.ws) { this.ws.onclose = null; this.ws.close() }
  }
}

export const backend = new BackendClient()
