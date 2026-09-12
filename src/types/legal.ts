export interface FeishuConfig {
  enabled: boolean
  appId: string
  appSecret: string
}

export interface WecomConfig {
  enabled: boolean
  corpId: string
  botId: string
  secret: string
}

export interface PracticeProfile {
  name: string
  firm: string
  title: string
  practiceAreas: string[]
  teamSize: 'solo' | 'small' | 'medium' | 'large'
  yearsOfPractice: number
  jurisdiction: string[]
  feishu: FeishuConfig
  wecom: WecomConfig
}

export interface Matter {
  id: string
  title: string
  caseNumber?: string
  client: string
  counterparty?: string
  practiceArea: string
  stage: MatterStage
  deadline?: string
  createdAt: Date
  updatedAt: Date
  description?: string
  customCategories?: string[]
  caseType?: 'civil' | 'criminal' | 'administrative' | 'commercial' | 'other'
  courtName?: string
  courtDate?: string
  opposingCounsel?: string
  // ── P1 扩展字段（2026-08）──
  /** 案由（最高法《民事案件案由规定》三级案由，如"民间借贷纠纷"） */
  caseCause?: string
  /** 审级（一审/二审/再审/执行/仲裁/非诉） */
  procedureStage?: ProcedureStage
  /** 诉讼请求标的额（元） */
  claimAmount?: number
  /** 委托人在案件中的角色 */
  clientRole?: ClientRole
  /** 受理日期（法院立案日，区别于 createdAt） */
  filingDate?: string
  /** 结案方式（仅 stage 为"已完成"或"已归档"时填写） */
  resolutionMethod?: ResolutionMethod
  /** 判决/调解结果摘要 */
  judgmentResult?: string
  /** 风险等级（律师工作量与败诉风险评估） */
  riskLevel?: RiskLevel
  /** 律师费金额（元） */
  fee?: number
  /** 收费方式 */
  feeType?: FeeType
  /** 多期限跟踪（P1 重构：替换单一 deadline 字段） */
  deadlines?: DeadlineItem[]
  /** 案件数据版本（用于数据迁移） */
  schemaVersion?: number
}

export type ProcedureStage = 'pre-filing' | 'first-instance' | 'second-instance' | 'retrial' | 'enforcement' | 'arbitration' | 'non-litigation'
export type ClientRole = 'plaintiff' | 'defendant' | 'third-party' | 'appellant' | 'appellee' | 'applicant' | 'respondent' | 'suspect' | 'defendant-criminal'
export type ResolutionMethod = 'judgment-plaintiff' | 'judgment-defendant' | 'judgment-partial' | 'mediation' | 'withdrawal' | 'settlement' | 'rejection' | 'transfer'
export type RiskLevel = 'high' | 'medium' | 'low'
export type FeeType = 'fixed' | 'hourly' | 'contingency' | 'hybrid'

/**
 * 法定期限类型（律师实务核心节点）
 * 用于 deadlines[] 数组的 type 字段
 */
export type DeadlineType =
  | 'filing'              // 立案期限
  | 'evidence'            // 举证期限
  | 'defense'             // 答辩期限
  | 'appeal-judgment'     // 判决上诉期（15日）
  | 'appeal-ruling'       // 裁定上诉期（10日）
  | 'appeal-criminal-judgment'  // 刑事判决上诉期（10日）
  | 'appeal-criminal-ruling'    // 刑事裁定上诉期（5日）
  | 'court-date'          // 开庭日期
  | 'enforcement'         // 申请执行期限（2年）
  | 'retrial'             // 申请再审期限（6个月）
  | 'jurisdiction'        // 管辖权异议期限
  | 'appraisal'           // 鉴定申请期限
  | 'preservation'        // 财产保全期限
  | 'arbitration-sue'     // 劳动仲裁起诉期（15日）
  | 'custom'              // 自定义期限

/**
 * 单一期限项
 */
/**
 * 期限的历史版本（双时间线模型，借鉴 semantica BiTemporalFact）。
 * 每次修改不覆盖旧数据，而是关闭旧版本的有效窗口（validUntil）并另起新版本——
 * 保证"当时为什么这么安排"永远可回溯，改期限本身成为审计记录。
 */
export interface DeadlineRevision {
  type: DeadlineType
  customLabel?: string
  /** 该版本的期限日期 */
  date: string
  note?: string
  /** 该版本生效时间（ISO） */
  validFrom: string
  /** 该版本被取代时间（ISO） */
  validUntil: string
  /** 变更原因（律师填写，可空） */
  changeReason?: string
}

export interface DeadlineItem {
  /** 期限 ID */
  id: string
  /** 期限类型 */
  type: DeadlineType
  /** 自定义类型名称（type='custom' 时使用） */
  customLabel?: string
  /** 期限日期（ISO 字符串） */
  date: string
  /** 备注 */
  note?: string
  /** 是否已完成（如已提交答辩状、已举证等） */
  completed?: boolean
  /** 创建时间 */
  createdAt: string
  /** 双时间线：当前版本生效时间（ISO） */
  validFrom?: string
  /** 双时间线：被取代时间；null/undefined = 现行有效。删除期限 = 关闭此窗口（软撤销，可恢复） */
  supersededAt?: string | null
  /** 既往版本（新 → 旧） */
  history?: DeadlineRevision[]
}

export type MatterStage = '待处理' | '审查中' | '证据收集' | '诉讼中' | '执行中' | '调解中' | '已完成' | '已归档'

export interface Session {
  id: string
  matterId?: string
  title: string
  createdAt: Date
  updatedAt: Date
  messageCount: number
  summary?: string
  /** Expert role system prompt attached to this session */
  systemPrompt?: string
  /** Which expert role this session belongs to (group.role) */
  expertRoleId?: string
}

export interface Citation {
  law: string
  article: string
  content: string
  source: string
  url?: string
  /** 已废止法律标记（由后端 extract_citations 本地数据库标注） */
  deprecated?: boolean
  /** 替代法律（如"民法典（第三编 合同）"） */
  replacedBy?: string
  /** 失效日期（如"2020-12-31"） */
  effectiveUntil?: string
  /** 废止说明 */
  deprecationNote?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  citations?: Citation[]
  reasoning?: string
  /** 本条回复是否为失败/错误提示（红色气泡 + 步骤面板失败态） */
  error?: boolean
  /** 本轮上下文注入统计（透明化上下文管理） */
  contextStats?: { history_rounds?: number; kb_chunks?: number; kb_docs?: number; experience?: number; files?: number }
}

export interface BackendChatResponse {
  response: string
  citations?: Citation[]
  reasoning?: string
  /** 后端识别到调用失败时为 true（如限流/Key 无效/网络超时） */
  error?: boolean
  context_stats?: { history_rounds?: number; kb_chunks?: number; kb_docs?: number; experience?: number; files?: number }
}

// ═══════════════════════════════════════════════════════════════
// AG-UI 协议事件类型 (参考 ag-ui.com/events.mdx 规范)
// 后端通过 WebSocket/Stdio 发送的每个流式事件都必须符合以下 schema
// ═══════════════════════════════════════════════════════════════

/** AG-UI 事件枚举（对齐官方 ag-ui 协议；LawClaw 扩展子集） */
export type AgUiEventType =
  | 'RUN_STARTED'
  | 'RUN_FINISHED'
  | 'RUN_ERROR'
  | 'STEP_STARTED'          // 扩展：步骤开始（官方仅 stepName，LawClaw 附加步骤面板字段）
  | 'STEP_FINISHED'
  | 'TEXT_MESSAGE_START'
  | 'TEXT_MESSAGE_CONTENT'
  | 'TEXT_MESSAGE_END'
  | 'TOOL_CALL_START'
  | 'TOOL_CALL_ARGS'
  | 'TOOL_CALL_END'
  | 'TOOL_CALL_RESULT'
  | 'REASONING_START'
  | 'REASONING_MESSAGE_CONTENT'  // 官方事件名（THINKING_* 与 REASONING_CONTENT 已废弃）
  | 'REASONING_END'
  | 'STATE_SNAPSHOT'
  | 'STATE_DELTA'
  | 'ACTIVITY_SNAPSHOT'
  | 'ACTIVITY_DELTA'

/** RUN 边界事件 — 一次用户提问对应一次完整 Run */
export interface RunStartedEvent {
  type: 'RUN_STARTED'
  runId: string
  /** 官方必填；LawClaw 语义 = 会话 ID */
  threadId: string
  startedAt?: string
  timestamp?: number          // 官方：ms epoch，每事件可选
}
export interface RunFinishedEvent {
  type: 'RUN_FINISHED'
  runId: string
  threadId?: string
  finishedAt?: string
  timestamp?: number
  /** 官方：outcome 仅 success | interrupt；错误终止走 RUN_ERROR（互斥） */
  outcome: {
    type: 'success' | 'interrupt'
    interrupts?: AgUiInterrupt[]
  }
  /** backward-compat — 最终响应内容（与旧协议 response 字段对齐） */
  finalResponse?: string
  citations?: Citation[]
}
/** 官方 RUN_ERROR：message 为顶层字符串；收到后不会再有 RUN_FINISHED */
export interface RunErrorEvent {
  type: 'RUN_ERROR'
  message: string
  code?: string
  runId?: string
  threadId?: string
  occurredAt?: string
  timestamp?: number
}

/** 步骤进度事件（官方必填 stepName；stepId/kind/title 等为 LawClaw 扩展） */
export interface StepStartedEvent {
  type: 'STEP_STARTED'
  stepName?: string
  runId: string
  stepId: string
  stepIndex: number           // 1-based，本次 run 中的第几步
  kind: 'tool' | 'think' | 'reply' | 'final'
  title: string               // 给用户看的中文标题，如「正在检索《民法典》...」
  description?: string
  startedAt?: string
  timestamp?: number
}
export interface StepFinishedEvent {
  type: 'STEP_FINISHED'
  stepName?: string
  runId: string
  stepId: string
  status: 'ok' | 'failed' | 'skipped'
  finishedAt?: string
  timestamp?: number
}

/** 文本消息（assistant）— 3 阶段：Start → N*Content → End */
export interface TextMessageStartEvent {
  type: 'TEXT_MESSAGE_START'
  runId: string
  messageId: string
  role: 'assistant' | 'user'
  createdAt: string
}
export interface TextMessageContentEvent {
  type: 'TEXT_MESSAGE_CONTENT'
  runId: string
  messageId: string
  delta: string
}
export interface TextMessageEndEvent {
  type: 'TEXT_MESSAGE_END'
  runId: string
  messageId: string
  citations?: Citation[]
  /** 完整最终文本（可选） */
  finalContent?: string
}

/** 工具调用 — 4 阶段：Start → N*Args → End → Result */
export interface ToolCallStartEvent {
  type: 'TOOL_CALL_START'
  toolCallId: string
  /** 官方必填 */
  toolCallName: string
  /** 官方字段名（messageId 为 LawClaw 扩展别名） */
  parentMessageId?: string
  runId: string
  messageId: string          // 绑定到哪条 assistant 消息
  toolName?: string          // 兼容别名 = toolCallName
  description?: string
  startedAt?: string
  timestamp?: number
}
export interface ToolCallArgsEvent {
  type: 'TOOL_CALL_ARGS'
  runId: string
  toolCallId: string
  delta: string              // 正在流式生成的参数 JSON 片段
}
export interface ToolCallEndEvent {
  type: 'TOOL_CALL_END'
  runId: string
  toolCallId: string
  finalArgs?: string         // 完整参数字符串（JSON）
  finishedAt: string
}
export interface ToolCallResultEvent {
  type: 'TOOL_CALL_RESULT'
  /** 官方必填：绑定的 assistant 消息 + 字符串化结果 */
  messageId?: string
  content?: string
  role?: 'tool'
  runId: string
  toolCallId: string
  result: unknown            // 工具调用返回的结果（LawClaw 扩展：原始对象）
  /** 展示策略：'hide' 不展示给律师，'preview' 只显示摘要，'full' 展开显示 */
  display?: 'hide' | 'preview' | 'full'
  preview?: string           // 摘要预览文本（display='preview' 时使用）
}

/** 推理链（Chain-of-Thought）— 官方 REASONING_* 家族 */
export interface ReasoningStartEvent {
  type: 'REASONING_START'
  runId: string
  messageId: string
  startedAt?: string
}
export interface ReasoningContentEvent {
  type: 'REASONING_MESSAGE_CONTENT'
  runId: string
  messageId: string
  delta: string
}
export interface ReasoningEndEvent {
  type: 'REASONING_END'
  runId: string
  messageId: string
  /** 跨轮次加密推理 CoT（可选） */
  encryptedValue?: string
}

/** 状态同步（Agent → Frontend） */
export interface StateSnapshotEvent {
  type: 'STATE_SNAPSHOT'
  runId: string
  path: string               // e.g. '/deadline/countdown'
  value: unknown
}
export interface StateDeltaEvent {
  type: 'STATE_DELTA'
  runId: string
  path: string
  delta: unknown             // JSON Patch: {op, path, value}[] 或合并增量
}

/** 活动消息（用户可观察到 Agent 正在做什么）— 对齐官方 ACTIVITY_SNAPSHOT/DELTA */
export interface ActivitySnapshotEvent {
  type: 'ACTIVITY_SNAPSHOT'
  runId: string
  messageId: string          // 官方必填：绑定消息
  activityType: string       // e.g. 'legal-search'
  content: Record<string, unknown>
  replace?: boolean
}
export interface ActivityDeltaEvent {
  type: 'ACTIVITY_DELTA'
  runId: string
  messageId: string
  activityType: string
  patch: unknown[]           // JSON Patch 增量
}

/** Interrupt — P2 人机协作：Agent 请求律师介入批准/确认 */
export interface AgUiInterrupt {
  id: string
  reason: 'tool_call' | 'input_required' | 'confirmation' | 'custom'
  reasonText?: string        // 中文说明（给律师看）
  message?: string           // 详细消息
  toolCallId?: string
  /** JSON Schema — 期望律师返回的表单结构 */
  responseSchema?: Record<string, unknown>
  expiresAt?: string
}

/** 联合类型 */
export type AgUiEvent =
  | RunStartedEvent | RunFinishedEvent | RunErrorEvent
  | StepStartedEvent | StepFinishedEvent
  | TextMessageStartEvent | TextMessageContentEvent | TextMessageEndEvent
  | ToolCallStartEvent | ToolCallArgsEvent | ToolCallEndEvent | ToolCallResultEvent
  | ReasoningStartEvent | ReasoningContentEvent | ReasoningEndEvent
  | StateSnapshotEvent | StateDeltaEvent
  | ActivitySnapshotEvent | ActivityDeltaEvent

/** chatStream 前端回调 — P0 向后兼容：保留 4 个经典回调 + 新增 onAgUiEvent 原始事件钩子 */
export interface ChatStreamCallbacks {
  /** 向后兼容旧代码 — 每个事件都会派发（在 onAgUiEvent 之后） */
  onDelta?: (chunk: string) => void
  onToolStart?: (name: string, args: unknown) => void
  onToolComplete?: (name: string, result: unknown) => void
  onThinking?: (text: string) => void
  /** P0/P1 新协议 — 可拿到完整 runId/messageId/toolCallId 状态机 */
  onAgUiEvent?: (event: AgUiEvent) => void
  /** Run 级回调（简化使用） */
  onRunStarted?: (runId: string) => void
  onRunFinished?: (event: RunFinishedEvent) => void
  onStepStarted?: (step: StepStartedEvent) => void
  onStepFinished?: (step: StepFinishedEvent) => void
}

export interface SearchResult {
  title: string
  article: string
  content: string
  source: string
  effective: boolean
}

export type QuickActionId = 'legal-research' | 'contract-review' | 'document-draft' | 'fee-calc' | 'limitation-calc'

export interface QuickAction {
  id: QuickActionId
  label: string
  icon: string
  description: string
  color: string
  prompt: string
}

// ── Legal Skill types ──
export interface LegalSkill {
  id: string
  name: string
  icon: string
  description: string
  prompt: string
  color: string
  group: string
  /** If set, invoking this skill calls backend RPC method instead of sending prompt */
  rpcMethod?: string
  /** RPC 检索通道：law=法规（默认）/ case=类案 / authoritative=权威案例 / case-by-law=法条反查 */
  searchType?: string
}

export type FileCategory = string

export interface ManagedFile {
  id: string
  name: string
  size: number
  type: string
  category: FileCategory
  matterId: string
  createdAt: Date
  data: string
  /** 已抽取的全文文本（后端解析适配层生成，供全文搜索/AI 知识库使用） */
  extractedText?: string
  /** 使用的解析器（pymupdf4llm/pymupdf/pdfminer/python-docx/openpyxl/plain） */
  extractor?: string
}

// ── Navigation types ──
export type AppView = 'dashboard' | 'assistant' | 'calendar' | 'cases' | 'files' | 'settings' | 'experts' | 'skills' | 'notification-test'
export type CaseSubView = 'list' | 'detail'

// ── Workspace types ──
export interface Workspace {
  id: string
  name: string
  description: string
  color: string
  createdAt: string
}

// ── Timeline types ──
export type TimelineEventType =
  | 'stage_change'
  | 'file_upload'
  | 'note'
  | 'session'
  | 'deadline'
  | 'court_date'
  | 'milestone'
  | 'decision'      // 律师决策记录（借鉴 semantica Decision-as-first-class：接案/调解/上诉等决策+理由沉淀为可查先例）

export interface TimelineEvent {
  id: string
  matterId: string
  type: TimelineEventType
  title: string
  description?: string
  createdAt: Date
  createdBy?: 'user' | 'system' | 'assistant'
  metadata?: Record<string, unknown>
}

// ── Schedule types ──
export type ScheduleType = 'court' | 'meeting' | 'deadline' | 'appointment' | 'personal'

export interface ScheduleItem {
  id: string
  title: string
  dateTime: string
  endDateTime?: string
  type: ScheduleType
  matterId?: string
  completed: boolean
  note?: string
  createdAt: string
}

// ── Enhanced Matter fields (for creation/editing) ──
export interface MatterFormData {
  title: string
  client: string
  counterparty?: string
  practiceArea: string
  stage: MatterStage
  caseNumber?: string
  description?: string
  caseType?: 'civil' | 'criminal' | 'administrative' | 'commercial' | 'other'
  courtName?: string
  courtDate?: string
  deadline?: string
  opposingCounsel?: string
  // P1 扩展字段
  caseCause?: string
  procedureStage?: ProcedureStage
  claimAmount?: number
  clientRole?: ClientRole
  filingDate?: string
  riskLevel?: RiskLevel
  fee?: number
  feeType?: FeeType
}

// ── Expert Group types ──
export type ExpertCategory = 'litigation' | 'industry' | 'corporate'

export interface ExpertRole {
  id: string
  name: string
  icon: string
  description: string
  color: string
  systemPrompt: string
  samplePrompt: string
  /** e.g. ['civil', 'criminal'] — which groups this role belongs to */
  groupId: string
}

export interface ExpertGroup {
  id: string
  name: string
  category: ExpertCategory
  icon: string
  description: string
  roles: ExpertRole[]
}
