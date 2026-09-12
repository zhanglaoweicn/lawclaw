/**
 * 案件模块共享常量
 *
 * 消除 ChatPanel / MatterList / CaseDetailView / CaseListView 中 4 份
 * 冗余的 stageColor / stageTagType 映射。
 */
import type { MatterStage, ProcedureStage, ClientRole, ResolutionMethod, RiskLevel, FeeType, DeadlineType, DeadlineItem } from '../types/legal'

export const ALL_STAGES: MatterStage[] = [
  '待处理', '审查中', '证据收集', '诉讼中', '执行中', '调解中', '已完成', '已归档',
]

/** 阶段 → 圆点颜色 */
export const STAGE_COLORS: Record<string, string> = {
  '待处理': '#8e8ea0',
  '审查中': '#b8973e',
  '证据收集': '#4a90d9',
  '诉讼中': '#b22222',
  '执行中': '#b45309',
  '调解中': '#7c3aed',
  '已完成': '#2d7d4e',
  '已归档': '#8e8ea0',
}

/** 阶段 → ElTag type */
export const STAGE_TAG_TYPES: Record<string, string> = {
  '待处理': 'info',
  '审查中': 'warning',
  '证据收集': 'warning',
  '诉讼中': 'danger',
  '执行中': 'warning',
  '调解中': 'warning',
  '已完成': 'success',
  '已归档': 'info',
}

export function stageColor(stage: string): string {
  return STAGE_COLORS[stage] || '#8e8ea0'
}

export function stageTagType(stage: string): string {
  return STAGE_TAG_TYPES[stage] || 'info'
}

/**
 * 法定期限（天数）—— 用于自动计算关键节点
 */
export const LEGAL_DEADLINES: Record<string, Record<string, number>> = {
  civil: {
    appeal: 15,           // 一审判决上诉期
    civilLawsuit: 36,     // 普通程序审理期限（可延长）
    summary: 30,           // 简易程序审理期限
    evidence: 15,          // 举证期限（一般）
    propertyPreservation: 5, // 保全裁定
  },
  criminal: {
    detention: 37,         // 拘留最长（含批捕）
    investigation: 60,     // 侦查一般
    reviewProsecute: 30,   // 审查起诉
    firstInstance: 90,     // 一审
    appeal: 10,            // 判决上诉期
  },
  labor: {
    arbitration: 45,       // 仲裁审理
    lawsuit: 15,           // 不服仲裁起诉期
  },
  admin: {
    lawsuit: 6,             // 行政起诉期（月）
    appeal: 15,            // 上诉期
  },
}

/**
 * 案件阶段允许的流转
 * key → 可以从 key 流转到的 stage 列表
 */
export const STAGE_TRANSITIONS: Record<string, MatterStage[]> = {
  '待处理': ['审查中', '已归档'],
  '审查中': ['证据收集', '诉讼中', '调解中', '已完成', '已归档'],
  '证据收集': ['诉讼中', '审查中', '调解中', '已完成', '已归档'],
  '诉讼中': ['调解中', '执行中', '已完成', '已归档'],
  '执行中': ['调解中', '已完成', '已归档'],
  '调解中': ['诉讼中', '执行中', '已完成', '已归档'],
  '已完成': ['执行中', '已归档'],
  '已归档': [],  // 不可流转
}

// ════════════════════════════════════════════════
//  P1 扩展常量（2026-08）
// ════════════════════════════════════════════════

/** 审级选项 */
export const PROCEDURE_STAGES: Array<{ value: ProcedureStage; label: string; desc: string }> = [
  { value: 'pre-filing', label: '诉前阶段', desc: '尚未立案：咨询、调解、保全准备' },
  { value: 'first-instance', label: '一审', desc: '基层/中级法院一审程序' },
  { value: 'second-instance', label: '二审', desc: '中级/高级法院上诉审' },
  { value: 'retrial', label: '再审', desc: '审判监督程序' },
  { value: 'enforcement', label: '执行', desc: '判决生效后强制执行程序' },
  { value: 'arbitration', label: '仲裁', desc: '劳动仲裁 / 商事仲裁' },
  { value: 'non-litigation', label: '非诉', desc: '法律咨询、合同审查、尽职调查等' },
]

export const PROCEDURE_STAGE_LABELS: Record<ProcedureStage, string> = {
  'pre-filing': '诉前',
  'first-instance': '一审',
  'second-instance': '二审',
  'retrial': '再审',
  'enforcement': '执行',
  'arbitration': '仲裁',
  'non-litigation': '非诉',
}

/** 委托人角色（按 caseType 分组） */
export const CLIENT_ROLES: Array<{ value: ClientRole; label: string; caseTypes: string[] }> = [
  { value: 'plaintiff', label: '原告', caseTypes: ['civil', 'administrative'] },
  { value: 'defendant', label: '被告', caseTypes: ['civil', 'administrative'] },
  { value: 'third-party', label: '第三人', caseTypes: ['civil', 'administrative'] },
  { value: 'appellant', label: '上诉人', caseTypes: ['civil', 'administrative', 'criminal'] },
  { value: 'appellee', label: '被上诉人', caseTypes: ['civil', 'administrative', 'criminal'] },
  { value: 'applicant', label: '申请人', caseTypes: ['civil', 'administrative'] },
  { value: 'respondent', label: '被申请人', caseTypes: ['civil', 'administrative'] },
  { value: 'suspect', label: '犯罪嫌疑人', caseTypes: ['criminal'] },
  { value: 'defendant-criminal', label: '被告人', caseTypes: ['criminal'] },
]

export const CLIENT_ROLE_LABELS: Record<ClientRole, string> = {
  'plaintiff': '原告',
  'defendant': '被告',
  'third-party': '第三人',
  'appellant': '上诉人',
  'appellee': '被上诉人',
  'applicant': '申请人',
  'respondent': '被申请人',
  'suspect': '犯罪嫌疑人',
  'defendant-criminal': '被告人',
}

/** 结案方式 */
export const RESOLUTION_METHODS: Array<{ value: ResolutionMethod; label: string; desc: string }> = [
  { value: 'judgment-plaintiff', label: '判决（原告胜诉）', desc: '法院判决支持原告诉讼请求' },
  { value: 'judgment-defendant', label: '判决（被告胜诉）', desc: '法院判决驳回原告诉讼请求' },
  { value: 'judgment-partial', label: '判决（部分胜诉）', desc: '法院判决部分支持原告诉讼请求' },
  { value: 'mediation', label: '调解结案', desc: '法院/仲裁调解书结案' },
  { value: 'withdrawal', label: '撤诉', desc: '原告撤回起诉' },
  { value: 'settlement', label: '和解', desc: '庭外和解后撤诉' },
  { value: 'rejection', label: '驳回起诉', desc: '法院裁定不予受理或驳回起诉' },
  { value: 'transfer', label: '移送管辖', desc: '移送其他法院/机关处理' },
]

export const RESOLUTION_METHOD_LABELS: Record<ResolutionMethod, string> = {
  'judgment-plaintiff': '判决（原告胜诉）',
  'judgment-defendant': '判决（被告胜诉）',
  'judgment-partial': '判决（部分胜诉）',
  'mediation': '调解结案',
  'withdrawal': '撤诉',
  'settlement': '和解',
  'rejection': '驳回起诉',
  'transfer': '移送管辖',
}

/** 风险等级 */
export const RISK_LEVELS: Array<{ value: RiskLevel; label: string; color: string }> = [
  { value: 'high', label: '高风险', color: '#f56c6c' },
  { value: 'medium', label: '中风险', color: '#e6a23c' },
  { value: 'low', label: '低风险', color: '#67c23a' },
]

export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  'high': '高风险',
  'medium': '中风险',
  'low': '低风险',
}

export function riskLevelColor(level: RiskLevel | undefined): string {
  if (!level) return '#8e8ea0'
  return RISK_LEVELS.find(r => r.value === level)?.color || '#8e8ea0'
}

/** 收费方式 */
export const FEE_TYPES: Array<{ value: FeeType; label: string; desc: string }> = [
  { value: 'fixed', label: '固定收费', desc: '按案件固定金额收费' },
  { value: 'hourly', label: '计时收费', desc: '按工作小时计费' },
  { value: 'contingency', label: '风险代理', desc: '按胜诉金额比例收费（最高 18%）' },
  { value: 'hybrid', label: '混合收费', desc: '基础费用 + 风险代理' },
]

export const FEE_TYPE_LABELS: Record<FeeType, string> = {
  'fixed': '固定',
  'hourly': '计时',
  'contingency': '风险',
  'hybrid': '混合',
}

/**
 * 常用案由（按业务领域分组，参考最高法《民事案件案由规定》2020 修订）
 * 仅列出律师高频案由，非全量
 */
export const COMMON_CASE_CAUSES: Record<string, string[]> = {
  '合同纠纷': [
    '买卖合同纠纷', '借款合同纠纷', '民间借贷纠纷', '建设工程施工合同纠纷',
    '房屋买卖合同纠纷', '租赁合同纠纷', '承揽合同纠纷', '运输合同纠纷',
    '保管合同纠纷', '委托合同纠纷', '保证合同纠纷', '保险合同纠纷',
  ],
  '婚姻家庭': [
    '离婚纠纷', '离婚后财产纠纷', '抚养纠纷', '扶养纠纷', '赡养纠纷',
    '收养关系纠纷', '分家析产纠纷', '法定继承纠纷', '遗嘱继承纠纷',
  ],
  '劳动争议': [
    '劳动合同纠纷', '劳动报酬纠纷', '经济补偿金纠纷', '违法解除劳动合同纠纷',
    '工伤待遇纠纷', '社会保险纠纷', '竞业限制纠纷',
  ],
  '知识产权': [
    '发明专利权权属、侵权纠纷', '实用新型专利权权属、侵权纠纷',
    '商标权权属、侵权纠纷', '著作权权属、侵权纠纷',
    '技术合同纠纷', '不正当竞争纠纷',
  ],
  '房产纠纷': [
    '房屋买卖合同纠纷', '商品房预售合同纠纷', '房屋租赁合同纠纷',
    '物权确认纠纷', '相邻关系纠纷', '业主共有权纠纷',
  ],
  '交通事故': [
    '机动车交通事故责任纠纷', '非机动车交通事故责任纠纷',
    '医疗损害责任纠纷', '教育机构责任纠纷', '违反安全保障义务责任纠纷',
  ],
  '刑事辩护': [
    '诈骗罪', '盗窃罪', '职务侵占罪', '危险驾驶罪', '交通肇事罪',
    '故意伤害罪', '非法吸收公众存款罪', '受贿罪', '贪污罪',
  ],
  // 以下三组与 PRACTICE_AREA_TO_CASE_TYPE 保持一致：缺项会导致
  // 民间借贷/行政诉讼/公司并购三类案件在新建时无法选择业务领域
  '民间借贷': [
    '民间借贷纠纷', '借款合同纠纷', '债权转让合同纠纷', '保证合同纠纷',
    '抵押合同纠纷', '质押合同纠纷', '不当得利纠纷',
  ],
  '行政诉讼': [
    '行政处罚纠纷', '行政强制措施纠纷', '行政不作为纠纷', '行政复议纠纷',
    '行政许可纠纷', '行政赔偿纠纷', '政府信息公开纠纷', '行政协议纠纷',
  ],
  '公司并购': [
    '股权转让纠纷', '公司决议效力确认纠纷', '股东资格确认纠纷',
    '股东知情权纠纷', '公司解散纠纷', '损害公司利益责任纠纷',
    '公司增资纠纷', '公司合并纠纷',
  ],
}

/** 业务领域 → 默认 caseType 映射 */
export const PRACTICE_AREA_TO_CASE_TYPE: Record<string, 'civil' | 'criminal' | 'administrative' | 'commercial'> = {
  '合同纠纷': 'civil',
  '婚姻家庭': 'civil',
  '劳动争议': 'civil',
  '民间借贷': 'civil',
  '知识产权': 'civil',
  '房产纠纷': 'civil',
  '交通事故': 'civil',
  '刑事辩护': 'criminal',
  '行政诉讼': 'administrative',
  '公司并购': 'commercial',
}

/**
 * 金额格式化（元 → 万元 / 元 显示）
 */
export function formatCurrency(amount: number | undefined): string {
  if (amount === undefined || amount === null || isNaN(amount)) return '-'
  if (amount >= 10000) {
    return `¥${(amount / 10000).toFixed(2)}万`
  }
  return `¥${amount.toFixed(2)}`
}

/**
 * 标的额 → 风险等级建议（律师工作量评估）
 */
export function suggestRiskLevel(claimAmount: number | undefined, caseType: string | undefined): RiskLevel {
  if (!claimAmount) return 'medium'
  if (caseType === 'criminal') return 'high'  // 刑事案件默认高风险
  if (claimAmount >= 1000000) return 'high'   // 100万以上
  if (claimAmount >= 100000) return 'medium'  // 10-100万
  return 'low'
}

// ════════════════════════════════════════════════
//  利益冲突检查（P1，2026-08）
//  依据：《律师法》第39条、《律师执业行为规范》第48条
// ════════════════════════════════════════════════

/** 冲突级别 */
export type ConflictLevel = 'none' | 'warning' | 'blocked'

export const CONFLICT_LEVEL_META: Record<ConflictLevel, { label: string; color: string; icon: string }> = {
  none: { label: '无冲突', color: '#67c23a', icon: '✓' },
  warning: { label: '潜在冲突', color: '#e6a23c', icon: '⚠' },
  blocked: { label: '利益冲突', color: '#f56c6c', icon: '⛔' },
}

/** 冲突类型 */
export type ConflictType =
  | 'same-client-as-counterparty'   // 委托人 = 某现有案件的对方当事人
  | 'same-counterparty-as-client'   // 对方当事人 = 某现有案件的委托人
  | 'same-opposing-counsel'         // 对方律师冲突（次要）
  | 'same-counterparty'             // 与现有案件的对方当事人相同（非冲突，仅提示）

/** 冲突检查结果 */
export interface ConflictMatch {
  /** 冲突级别 */
  level: ConflictLevel
  /** 冲突类型 */
  type: ConflictType
  /** 冲突描述 */
  description: string
  /** 相关案件 ID */
  matterId: string
  /** 相关案件标题 */
  matterTitle: string
  /** 相关案件阶段 */
  matterStage: string
  /** 冲突字段（client / counterparty / opposingCounsel） */
  field: 'client' | 'counterparty' | 'opposingCounsel'
  /** 匹配的值 */
  matchedValue: string
}

/**
 * 名称标准化：去除括号注释、空格、统一简繁
 * 例如 "华盛贸易有限公司" 与 "华盛贸易有限公司（借款方）" 应匹配
 */
export function normalizePartyName(name: string): string {
  if (!name) return ''
  return name
    .replace(/[（(][^)）]*[)）]/g, '')  // 去除括号注释
    .replace(/\s+/g, '')                  // 去除空白
    .trim()
}

/**
 * 名称匹配判定：完全匹配 或 包含关系（一方是另一方的前缀/子串）
 * 例如 "宏远地产" 匹配 "宏远地产集团北京有限公司"
 */
export function isPartyMatch(a: string, b: string): boolean {
  const na = normalizePartyName(a)
  const nb = normalizePartyName(b)
  if (!na || !nb) return false
  if (na === nb) return true
  // 至少 4 字符且一方包含另一方
  if (na.length >= 4 && nb.length >= 4) {
    if (na.includes(nb) || nb.includes(na)) return true
  }
  return false
}

// ════════════════════════════════════════════════
//  多期限跟踪（P1 重构，2026-08）
// ════════════════════════════════════════════════

/** 期限类型元数据 */
export const DEADLINE_TYPES: Array<{
  value: DeadlineType
  label: string
  desc: string
  legalBasis?: string
  color: string
}> = [
  { value: 'filing',          label: '立案期限',     desc: '法院立案审查期限（7日内决定是否立案）', color: '#4a90d9' },
  { value: 'evidence',        label: '举证期限',     desc: '法院指定的举证期限（一般不少于15日）', legalBasis: '民诉法第65条', color: '#b8973e' },
  { value: 'defense',         label: '答辩期限',     desc: '一审15日 / 二审10日（自收到起诉状之日起）', legalBasis: '民诉法第128条', color: '#b8973e' },
  { value: 'appeal-judgment', label: '判决上诉期',   desc: '一审判决上诉期15日（自送达之日起算）', legalBasis: '民诉法第171条', color: '#b22222' },
  { value: 'appeal-ruling',   label: '裁定上诉期',   desc: '一审裁定上诉期10日（自送达之日起算）', legalBasis: '民诉法第171条', color: '#b22222' },
  { value: 'appeal-criminal-judgment', label: '刑事判决上诉期', desc: '刑事一审判决上诉/抗诉期10日（自送达之日起算）', legalBasis: '刑诉法第230条', color: '#b22222' },
  { value: 'appeal-criminal-ruling',   label: '刑事裁定上诉期', desc: '刑事一审裁定上诉/抗诉期5日（自送达之日起算）', legalBasis: '刑诉法第230条', color: '#b22222' },
  { value: 'court-date',      label: '开庭日期',     desc: '法院通知的开庭时间', color: '#7c3aed' },
  { value: 'enforcement',     label: '申请执行期限', desc: '履行期届满后2年内（民事）/ 6个月（行政）', legalBasis: '民诉法第246条', color: '#b45309' },
  { value: 'retrial',         label: '申请再审期限', desc: '判决生效后6个月内', legalBasis: '民诉法第206条', color: '#b45309' },
  { value: 'jurisdiction',    label: '管辖权异议期', desc: '提交答辩状期间内（一审15日内）', legalBasis: '民诉法第127条', color: '#b8973e' },
  { value: 'appraisal',       label: '鉴定申请期',   desc: '举证期限内提出鉴定申请', legalBasis: '民诉法证据规定', color: '#b8973e' },
  { value: 'preservation',    label: '财产保全期',   desc: '诉前保全后30日内必须起诉', legalBasis: '民诉法第104条', color: '#b22222' },
  { value: 'arbitration-sue', label: '仲裁起诉期',   desc: '收到劳动仲裁裁决书15日内向法院起诉', legalBasis: '劳动争议调解仲裁法第50条', color: '#b22222' },
  { value: 'custom',          label: '自定义期限',   desc: '其他法定期限或约定期限', color: '#8e8ea0' },
]

export const DEADLINE_TYPE_LABELS: Record<DeadlineType, string> = DEADLINE_TYPES.reduce(
  (acc, item) => { acc[item.value] = item.label; return acc },
  {} as Record<DeadlineType, string>
)

export function deadlineTypeLabel(type: DeadlineType): string {
  return DEADLINE_TYPE_LABELS[type] || '其他期限'
}

export function deadlineTypeColor(type: DeadlineType): string {
  return DEADLINE_TYPES.find(t => t.value === type)?.color || '#8e8ea0'
}

/** 生成期限 ID */
export function generateDeadlineId(): string {
  return 'dl-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
}

/**
 * 获取案件最近的一个未完成期限
 * 用于列表显示"最近 deadline"
 */
export function getNearestDeadline(deadlines: DeadlineItem[] | undefined): DeadlineItem | null {
  if (!deadlines || deadlines.length === 0) return null
  const now = Date.now()
  const upcoming = deadlines
    .filter(d => !d.completed && !d.supersededAt)
    .map(d => ({ ...d, _diff: new Date(d.date).getTime() - now }))
    .sort((a, b) => a._diff - b._diff)
  // 优先返回未过期的最近期限，若无则返回逾期最久的
  const future = upcoming.find(d => d._diff >= 0)
  return (future || upcoming[0] || null) as DeadlineItem | null
}

/**
 * 获取案件所有现行有效且未完成的期限（按日期升序）
 * 双时间线：排除已撤销（supersededAt 非空 = 旧版本已关窗）
 */
export function getActiveDeadlines(deadlines: DeadlineItem[] | undefined): DeadlineItem[] {
  if (!deadlines) return []
  return deadlines
    .filter(d => !d.completed && !d.supersededAt)
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
}

/**
 * 计算期限剩余天数
 */
export function daysRemaining(dateStr: string): number {
  const d = new Date(dateStr)
  const now = Date.now()
  return Math.ceil((d.getTime() - now) / 86400000)
}

/**
 * 期限紧急程度
 * - overdue: 已逾期
 * - critical: 3日内
 * - warning: 7日内
 * - soon: 30日内
 * - normal: 30日以上
 */
export type DeadlineUrgency = 'overdue' | 'critical' | 'warning' | 'soon' | 'normal'

export function deadlineUrgency(dateStr: string): DeadlineUrgency {
  const days = daysRemaining(dateStr)
  if (days < 0) return 'overdue'
  if (days <= 3) return 'critical'
  if (days <= 7) return 'warning'
  if (days <= 30) return 'soon'
  return 'normal'
}

export const DEADLINE_URGENCY_META: Record<DeadlineUrgency, { label: string; color: string; bg: string }> = {
  overdue:  { label: '已逾期', color: '#f56c6c', bg: 'rgba(245, 108, 108, 0.1)' },
  critical: { label: '紧急',   color: '#f56c6c', bg: 'rgba(245, 108, 108, 0.06)' },
  warning:  { label: '即将到期', color: '#e6a23c', bg: 'rgba(230, 162, 60, 0.06)' },
  soon:     { label: '近期',   color: '#b8973e', bg: 'rgba(184, 151, 62, 0.04)' },
  normal:   { label: '正常',   color: '#67c23a', bg: 'rgba(103, 194, 58, 0.04)' },
}

/**
 * 格式化期限显示文案
 */
export function formatDeadline(dateStr: string): string {
  const days = daysRemaining(dateStr)
  if (days < 0) return `逾期 ${Math.abs(days)} 天`
  if (days === 0) return '今天到期'
  if (days <= 30) return `剩 ${days} 天`
  return `${days} 天后`
}
