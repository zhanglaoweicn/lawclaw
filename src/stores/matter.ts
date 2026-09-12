import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Matter, MatterStage, DeadlineItem, DeadlineType } from '../types/legal'
import { seedAllDemoCases } from '../seed/seedCaseData'
import { isDemoBuild } from '../lib/buildFlavor'
import {
  STAGE_COLORS, STAGE_TAG_TYPES, stageColor, stageTagType, ALL_STAGES, STAGE_TRANSITIONS,
  suggestRiskLevel, PRACTICE_AREA_TO_CASE_TYPE,
  isPartyMatch, type ConflictMatch, type ConflictLevel,
  generateDeadlineId, getNearestDeadline, getActiveDeadlines,
} from '../lib/caseConstants'

const MATTERS_KEY = 'lawclaw_matters'
const SEED_FLAG = 'lawclaw_seeded'

/** 当前 schema 版本（用于数据迁移） */
const CURRENT_SCHEMA_VERSION = 4

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

/**
 * 数据迁移：将旧版本 Matter 升级到当前 schema
 * - v1 → v2: 补充 P1 扩展字段（caseCause/procedureStage/claimAmount/clientRole 等）
 * - v2 → v3: 将单一 deadline + courtDate 转换为 deadlines[] 数组
 */
function migrateMatter(m: any): Matter {
  // 通用字段补全
  const migrated: Matter = {
    ...m,
    createdAt: m.createdAt ? new Date(m.createdAt) : new Date(),
    updatedAt: m.updatedAt ? new Date(m.updatedAt) : new Date(),
  }
  // v1 → v2: 根据 practiceArea 推断 caseCause 和 procedureStage
  if (!migrated.schemaVersion || migrated.schemaVersion < 2) {
    // 推断 procedureStage：基于 stage
    if (!migrated.procedureStage) {
      if (migrated.stage === '待处理') migrated.procedureStage = 'pre-filing'
      else if (migrated.stage === '已完成' || migrated.stage === '已归档') {
        migrated.procedureStage = migrated.caseType === 'criminal' ? 'first-instance' : 'first-instance'
      } else {
        migrated.procedureStage = 'first-instance'
      }
    }
    // 推断 caseCause：基于 practiceArea（粗略映射）
    if (!migrated.caseCause && migrated.practiceArea) {
      migrated.caseCause = migrated.practiceArea  // 临时使用 practiceArea 作为 caseCause
    }
    // 推断 riskLevel
    if (!migrated.riskLevel) {
      migrated.riskLevel = suggestRiskLevel(migrated.claimAmount, migrated.caseType)
    }
  }
  // v2 → v3: 转换 deadline + courtDate 为 deadlines[]
  if (!migrated.schemaVersion || migrated.schemaVersion < 3) {
    if (!migrated.deadlines) migrated.deadlines = []
    // 旧 deadline 字段转为 'evidence' 类型（最常见的举证/答辩截止）
    if (migrated.deadline && !migrated.deadlines.find((d: DeadlineItem) => d.date === migrated.deadline)) {
      migrated.deadlines.push({
        id: generateDeadlineId(),
        type: 'evidence' as DeadlineType,
        date: migrated.deadline,
        note: '迁移自旧 deadline 字段（原为举证/答辩截止）',
        completed: false,
        createdAt: new Date().toISOString(),
      })
    }
    // 旧 courtDate 字段转为 'court-date' 类型
    if (migrated.courtDate && !migrated.deadlines.find((d: DeadlineItem) => d.date === migrated.courtDate)) {
      migrated.deadlines.push({
        id: generateDeadlineId(),
        type: 'court-date' as DeadlineType,
        date: migrated.courtDate,
        note: '迁移自旧 courtDate 字段',
        completed: false,
        createdAt: new Date().toISOString(),
      })
    }
  }
  // v3 → v4: 期限补双时间线字段（借鉴 semantica BiTemporalFact——
  // validFrom=版本生效时间，supersededAt=null 表示现行有效，history 存既往版本）。
  // 自愈式：按字段缺失判断而非版本号——种子数据/老数据直接标 v4 也能补齐（幂等）
  for (const dl of migrated.deadlines || []) {
    if (!dl.validFrom) dl.validFrom = dl.createdAt || new Date().toISOString()
    if (dl.supersededAt === undefined) dl.supersededAt = null
    if (!dl.history) dl.history = []
  }
  migrated.schemaVersion = CURRENT_SCHEMA_VERSION
  return migrated
}

function loadMatters(): Matter[] {
  try {
    const raw = localStorage.getItem(MATTERS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw, (k, v) => k === 'createdAt' || k === 'updatedAt' ? new Date(v) : v)
      // 迁移旧数据
      return (Array.isArray(parsed) ? parsed : []).map(migrateMatter)
    }
  } catch {
    return []
  }
  // ── Auto-seed demo data only on first-ever load ──
  // If seed flag exists, user has explicitly cleared data — don't re-seed
  if (localStorage.getItem(SEED_FLAG)) return []
  // 客户版（VITE_LAWCLAW_FLAVOR=clean）首启即空台账：交付给客户的版本不含任何演示数据
  if (!isDemoBuild) {
    localStorage.setItem(SEED_FLAG, '1')
    return []
  }
  localStorage.setItem(SEED_FLAG, '1')

  const now = Date.now()
  const DAY = 86400000
  const t = (da: number) => new Date(now - da * DAY)
  const demo: Matter[] = [
    {
      id: generateId(), title: '华盛公司与明远公司借贷合同纠纷', caseNumber: '(2026)沪0105民初8273号',
      client: '华盛贸易有限公司', counterparty: '明远建设工程有限公司',
      practiceArea: '合同纠纷', caseCause: '民间借贷纠纷',
      stage: '诉讼中', procedureStage: 'first-instance', caseType: 'civil',
      clientRole: 'plaintiff', claimAmount: 5200000, riskLevel: 'high',
      deadline: t(-30).toISOString(), filingDate: t(60).toISOString(),
      courtName: '上海市长宁区人民法院', courtDate: t(-15).toISOString(),
      description: '2025年3月华盛公司出借500万元，明远公司仅付三个月利息后逾期未还。诉请偿还本金500万元及利息。',
      opposingCounsel: '郑国辉 律师',
      fee: 150000, feeType: 'hybrid',
      createdAt: t(180), updatedAt: new Date(),
      customCategories: ['案件文书', '证据材料', '对方提交', '法院文书'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
    {
      id: generateId(), title: '张某诉李某离婚纠纷', caseNumber: '(2026)京0105民初4621号',
      client: '张某（女方）', counterparty: '李某（男方）',
      practiceArea: '婚姻家庭', caseCause: '离婚纠纷',
      stage: '诉讼中', procedureStage: 'first-instance', caseType: 'civil',
      clientRole: 'plaintiff', claimAmount: 2800000, riskLevel: 'medium',
      filingDate: t(40).toISOString(),
      courtName: '北京市朝阳区人民法院', courtDate: t(-10).toISOString(),
      description: '张女士诉请离婚、孩子抚养权及分割共同财产约280万元，男方不同意离婚。',
      opposingCounsel: '方芳 律师',
      fee: 30000, feeType: 'fixed',
      createdAt: t(120), updatedAt: new Date(),
      customCategories: ['婚姻家庭', '证据材料', '财产清单'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
    {
      id: generateId(), title: '周某诉王某民间借贷纠纷', caseNumber: '(2026)粤0304民初12568号',
      client: '周建军', counterparty: '王海明',
      practiceArea: '民间借贷', caseCause: '民间借贷纠纷',
      stage: '证据收集', procedureStage: 'pre-filing', caseType: 'civil',
      clientRole: 'plaintiff', claimAmount: 950000, riskLevel: 'medium',
      deadline: t(-3).toISOString(),
      courtName: '深圳市福田区人民法院',
      description: '2024年王某借款80万元后仅付2个月利息即失联，追讨本息约95万元。',
      fee: 50000, feeType: 'contingency',
      createdAt: t(60), updatedAt: new Date(),
      customCategories: ['借贷证据', '案件文书'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
    {
      id: generateId(), title: '天行科技诉蓝海公司发明专利侵权纠纷', caseNumber: '(2026)最高法知民终189号',
      client: '天行科技股份有限公司', counterparty: '蓝海科技（深圳）有限公司',
      practiceArea: '知识产权', caseCause: '发明专利权权属、侵权纠纷',
      stage: '诉讼中', procedureStage: 'second-instance', caseType: 'civil',
      clientRole: 'appellant', claimAmount: 3000000, riskLevel: 'high',
      deadline: t(-30).toISOString(), filingDate: t(330).toISOString(),
      courtName: '最高人民法院知识产权法庭', courtDate: t(-7).toISOString(),
      description: 'AI图像识别专利侵权案，一审判赔300万元，被告上诉至最高院。',
      opposingCounsel: '陈思远 律师',
      fee: 200000, feeType: 'hybrid',
      createdAt: t(365), updatedAt: new Date(),
      customCategories: ['专利文件', '侵权证据', '法律文书'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
    {
      id: generateId(), title: '赵某诉钱某交通事故人身损害赔偿纠纷', caseNumber: '(2026)京0115民初3692号',
      client: '赵晓东（受害方）', counterparty: '钱大军、长兴财险北京分公司',
      practiceArea: '交通事故', caseCause: '机动车交通事故责任纠纷',
      stage: '调解中', procedureStage: 'first-instance', caseType: 'civil',
      clientRole: 'plaintiff', claimAmount: 386000, riskLevel: 'low',
      deadline: t(-20).toISOString(), filingDate: t(70).toISOString(),
      courtName: '北京市大兴区人民法院',
      description: '交通事故十级伤残，起诉要求赔偿38.6万元，法院正组织调解。',
      opposingCounsel: '刘文杰 律师（长兴财险）',
      fee: 20000, feeType: 'contingency',
      createdAt: t(90), updatedAt: new Date(),
      customCategories: ['案件文书', '医疗证据', '赔偿清单'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
    {
      id: generateId(), title: '孙某诉辉煌科技有限公司违法解除劳动合同纠纷', caseNumber: '京劳人仲字(2026)第1582号',
      client: '孙丽华（员工）', counterparty: '辉煌科技有限公司',
      practiceArea: '劳动争议', caseCause: '违法解除劳动合同纠纷',
      stage: '审查中', procedureStage: 'arbitration', caseType: 'civil',
      clientRole: 'applicant', claimAmount: 400000, riskLevel: 'medium',
      deadline: t(-25).toISOString(),
      courtName: '北京市劳动人事争议仲裁委员会',
      description: '工作近8年被裁员，主张违法解除赔偿金2N共40万元。',
      fee: 15000, feeType: 'contingency',
      createdAt: t(45), updatedAt: new Date(),
      customCategories: ['案件文书', '劳动合同', '工资证据'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
    {
      id: generateId(), title: '吴某等32户业主诉宏远地产房屋买卖合同纠纷（集体诉讼）', caseNumber: '(2026)京0108民初21037号',
      client: '吴建华等32户业主', counterparty: '宏远地产集团北京有限公司',
      practiceArea: '房产纠纷', caseCause: '房屋买卖合同纠纷',
      stage: '证据收集', procedureStage: 'first-instance', caseType: 'civil',
      clientRole: 'plaintiff', claimAmount: 9600000, riskLevel: 'high',
      deadline: t(-30).toISOString(), filingDate: t(20).toISOString(),
      courtName: '北京市海淀区人民法院',
      description: '宏远华府项目停工超18个月，32户业主集体维权，诉请解除合同并返还购房款。',
      opposingCounsel: '宏远法务团队',
      fee: 300000, feeType: 'hybrid',
      createdAt: t(30), updatedAt: new Date(),
      customCategories: ['购房合同', '付款证据', '法律文书'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
    // 新增：覆盖完整生命周期 — 已完成案件
    {
      id: generateId(), title: '李某诉某餐饮公司工伤待遇纠纷', caseNumber: '(2025)京0105民初9321号',
      client: '李建国', counterparty: '某餐饮管理有限公司',
      practiceArea: '劳动争议', caseCause: '工伤待遇纠纷',
      stage: '已完成', procedureStage: 'first-instance', caseType: 'civil',
      clientRole: 'plaintiff', claimAmount: 185000, riskLevel: 'low',
      filingDate: t(200).toISOString(),
      courtName: '北京市朝阳区人民法院',
      description: '厨房工伤九级伤残，诉请工伤待遇赔偿18.5万元。',
      resolutionMethod: 'mediation', judgmentResult: '调解结案，被告赔偿16.8万元，分两期支付',
      fee: 8000, feeType: 'contingency',
      createdAt: t(220), updatedAt: t(100),
      customCategories: ['案件文书', '工伤认定', '医疗证据'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
    // 新增：覆盖完整生命周期 — 已归档案件
    {
      id: generateId(), title: '王某诉某保险公司财产保险合同纠纷', caseNumber: '(2025)沪0101民初5638号',
      client: '王志强', counterparty: '某财产保险股份有限公司上海分公司',
      practiceArea: '合同纠纷', caseCause: '保险合同纠纷',
      stage: '已归档', procedureStage: 'first-instance', caseType: 'civil',
      clientRole: 'plaintiff', claimAmount: 320000, riskLevel: 'low',
      filingDate: t(400).toISOString(),
      courtName: '上海市黄浦区人民法院',
      description: '车辆事故后保险公司拒赔，诉请支付保险金32万元。',
      resolutionMethod: 'judgment-plaintiff', judgmentResult: '判决支持原告诉请，被告支付保险金30.5万元及利息',
      fee: 25000, feeType: 'contingency',
      createdAt: t(420), updatedAt: t(280),
      customCategories: ['案件文书', '保险合同', '判决书'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
    // 新增：覆盖完整生命周期 — 执行中案件
    {
      id: generateId(), title: '刘某诉某实业公司民间借贷纠纷（执行阶段）', caseNumber: '(2025)京0105民初8821号 / (2026)京0105执3456号',
      client: '刘建国', counterparty: '某实业发展有限公司',
      practiceArea: '民间借贷', caseCause: '民间借贷纠纷',
      stage: '执行中', procedureStage: 'enforcement', caseType: 'civil',
      clientRole: 'applicant', claimAmount: 2800000, riskLevel: 'high',
      deadline: t(-12).toISOString(), filingDate: t(500).toISOString(),
      courtName: '北京市朝阳区人民法院（执行局）',
      description: '一审判决支持本息280万元，对方未履行，已申请强制执行。正在查封对方公司银行账户、车辆及办公设备。',
      resolutionMethod: 'judgment-plaintiff', judgmentResult: '判决原告胜诉，被告应偿还借款本金260万及利息（截止起诉日约20万元）',
      fee: 80000, feeType: 'contingency',
      createdAt: t(520), updatedAt: t(30),
      customCategories: ['案件文书', '判决书', '执行材料', '财产线索'],
      schemaVersion: CURRENT_SCHEMA_VERSION,
    },
  ]
  // 先对前 9 个案件（已有 deadline/courtDate）应用 v2→v3 迁移
  const migrated = demo.map(m => {
    const m2 = { ...m, schemaVersion: 2 }
    return migrateMatter(m2)
  })

  // ════════════════════════════════════════════════════
  //  多期限测试案件：覆盖 12 种 DeadlineType
  //  刻意覆盖逾期/临界/紧急/近期/正常各档，用于验证 Dashboard 聚合效果
  // ════════════════════════════════════════════════════
  function dlOffset(type: DeadlineType, offsetDays: number, note = '', completed = false, customLabel?: string): DeadlineItem {
    const d = new Date()
    d.setDate(d.getDate() + offsetDays)
    return {
      id: generateDeadlineId(),
      type,
      customLabel,
      date: d.toISOString(),
      note,
      completed,
      createdAt: new Date().toISOString(),
    }
  }

  const deadlinesTest: DeadlineItem[] = [
    // 已逾期（逾期天数多到能被 Dashboard 捕获：-30天内）
    dlOffset('jurisdiction',  -12, '管辖权异议期：自收到起诉状之日起15日内 → 已逾期12天！'),
    dlOffset('arbitration-sue',  -4, '收到劳动仲裁裁决书15日内起诉 → 已逾期4天！'),

    // 今天到期（critical）
    dlOffset('evidence',         0, '举证期限截止日（今日必须提交最后一份证据）'),

    // 3日内（critical）
    dlOffset('defense',          2, '一审答辩期限15日：还有2天，需准备管辖异议申请'),

    // 7日内（warning）
    dlOffset('preservation',     6, '诉前保全后30日内必须起诉 → 还有6天'),

    // 10日内（soon）
    dlOffset('appeal-ruling',   10, '一审裁定上诉期10日：一审驳回起诉裁定'),

    // 15日内（soon）
    dlOffset('appeal-judgment', 13, '一审判决上诉期15日：一审判决败诉，准备上诉'),

    // 20日内（soon - 自定义）
    dlOffset('custom',          20, '申请执行和解协议签署期限', false, '执行和解期限'),

    // 30日内（soon）
    dlOffset('enforcement',     25, '一审判决履行期届满后2年内申请强制执行'),

    // 45日后（normal - 已超30天，Dashboard 不会展示）
    dlOffset('appraisal',       45, '举证期限内申请笔迹鉴定'),

    // 90日后（normal）
    dlOffset('retrial',         90, '二审判决生效后6个月内申请再审'),

    // 已完成（应该被 Dashboard/详情页过滤掉）
    dlOffset('filing',          -60, '已立案：北京海淀区法院（2026）京0108民初12345号', true),
  ]

  migrated.push({
    id: generateId(),
    title: '【测试用】多期限综合案件 — 期限跟踪测试基准',
    caseNumber: '(2026)京0108民初12345号',
    client: '测试委托方 — 多期限验证有限公司',
    counterparty: '测试对方 — 北京某电子商务公司',
    opposingCounsel: '张XX律师',
    practiceArea: '民商事诉讼',
    caseCause: '买卖合同纠纷',
    caseType: 'civil',
    procedureStage: 'first-instance',
    clientRole: 'plaintiff',
    stage: '诉讼中',
    claimAmount: 1800000,
    riskLevel: 'high',
    courtName: '北京市海淀区人民法院',
    filingDate: new Date(Date.now() - 30 * 86400000).toISOString(),
    description: '【测试用】本案件用于验证多期限系统的 Dashboard 聚合效果。\n包含 12 种不同期限类型：管辖权异议（逾期12天）、仲裁起诉（逾期4天）、举证（今天到期）、答辩（剩2天）、财产保全（剩6天）、裁定上诉（剩10天）、判决上诉（剩13天）、自定义-执行和解（剩20天）、申请执行（剩25天）、鉴定申请（45天）、再审（90天）、已完成立案（60天前）。\n律师可以在 Dashboard 紧急期限卡片中验证聚合结果。',
    fee: 80000,
    feeType: 'fixed',
    deadlines: deadlinesTest,
    createdAt: new Date(Date.now() - 30 * 86400000),
    updatedAt: new Date(),
    customCategories: ['案件文书', '证据材料', '期限跟踪'],
    schemaVersion: 3,
  })

  // 演示版同样剔除标题含「测试用」的基准数据——客户演示时不该出现"测试"字样
  const demoClean = migrated.filter(m => !/测试用|测试基准/.test(m.title))
  saveMatters(demoClean)
  return demoClean
}

function saveMatters(matters: Matter[]) {
  try {
    localStorage.setItem(MATTERS_KEY, JSON.stringify(matters))
  } catch (e) {
    console.error('[matter] saveMatters failed:', e)
    // localStorage 配额超限时尝试清除 archived 案件后重试
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      const active = matters.filter(m => m.stage !== '已归档')
      try {
        localStorage.setItem(MATTERS_KEY, JSON.stringify(active))
        console.warn('[matter] 已自动清理已归档案件以释放存储空间')
      } catch {
        // 最终兜底
      }
    }
  }
}

const STAGES = ALL_STAGES

export const useMatterStore = defineStore('matter', () => {
  const matters = ref<Matter[]>(loadMatters())
  const activeMatterId = ref<string | null>(null)

  const activeMatter = computed(() => matters.value.find(m => m.id === activeMatterId.value) || null)

  const activeMatters = computed(() => matters.value.filter(m => m.stage !== '已归档' && m.stage !== '已完成'))
  const archivedMatters = computed(() => matters.value.filter(m => m.stage === '已归档' || m.stage === '已完成'))

  const mattersByStage = computed(() => {
    const map: Record<string, Matter[]> = {}
    for (const s of STAGES) map[s] = []
    for (const m of matters.value) {
      // 防御：若 stage 是非法值（旧数据），归入"待处理"
      const stage = map[m.stage] ? m.stage : '待处理'
      map[stage].push(m)
    }
    return map
  })

  function addMatter(m: Omit<Matter, 'id' | 'createdAt' | 'updatedAt'>): Matter {
    const now = new Date()
    // 若 form.deadline 存在但 deadlines[] 未提供，自动转换（向后兼容快捷输入）
    let deadlines = m.deadlines
    if (!deadlines && m.deadline) {
      deadlines = [{
        id: generateDeadlineId(),
        type: 'evidence' as DeadlineType,
        date: m.deadline,
        note: '创建案件时快捷输入的截止日期',
        completed: false,
        createdAt: now.toISOString(),
      }]
    }
    if (m.courtDate && deadlines) {
      // 若 courtDate 存在且 deadlines 中没有 court-date 类型，自动添加
      const hasCourtDate = deadlines.find(d => d.type === 'court-date')
      if (!hasCourtDate) {
        deadlines.push({
          id: generateDeadlineId(),
          type: 'court-date' as DeadlineType,
          date: m.courtDate,
          note: '开庭日期',
          completed: false,
          createdAt: now.toISOString(),
        })
      }
    }
    const matter: Matter = {
      ...m,
      deadlines,
      id: generateId(), createdAt: now, updatedAt: now,
      schemaVersion: CURRENT_SCHEMA_VERSION,
      // 若未指定风险等级，根据标的额自动建议
      riskLevel: m.riskLevel || suggestRiskLevel(m.claimAmount, m.caseType),
    }
    matters.value.unshift(matter)
    saveMatters(matters.value)
    // Auto-create timeline event for case creation
    import('../stores/timeline').then(({ useTimelineStore }) => {
      useTimelineStore().addEvent({
        matterId: matter.id,
        type: 'milestone',
        title: '案件创建',
        description: `案件「${matter.title}」创建`,
        createdBy: 'user',
      })
    })
    return matter
  }

  function updateMatter(id: string, updates: Partial<Matter>) {
    const idx = matters.value.findIndex(m => m.id === id)
    if (idx === -1) return
    const prev = matters.value[idx]
    const prevStage = prev.stage

    // Validate stage transitions
    if (updates.stage && updates.stage !== prevStage) {
      const allowed = STAGE_TRANSITIONS[prevStage] || []
      if (!allowed.includes(updates.stage)) {
        console.warn(`阶段变更不允许: ${prevStage} → ${updates.stage}`)
        // Still proceed — don't block user, but log warning
      }
    }

    matters.value[idx] = { ...prev, ...updates, updatedAt: new Date() }
    saveMatters(matters.value)

    // Auto-create timeline event on stage change
    if (updates.stage && updates.stage !== prevStage) {
      import('../stores/timeline').then(({ useTimelineStore }) => {
        useTimelineStore().addEvent({
          matterId: id,
          type: 'stage_change',
          title: `阶段变更: ${prevStage} → ${updates.stage}`,
          createdBy: 'system',
          metadata: { fromStage: prevStage, toStage: updates.stage },
        })
      })
    }
  }

  function deleteMatter(id: string) {
    matters.value = matters.value.filter(m => m.id !== id)
    if (activeMatterId.value === id) activeMatterId.value = null
    saveMatters(matters.value)

    // Cascade: clean up related data
    import('../stores/timeline').then(({ useTimelineStore }) => {
      useTimelineStore().clearMatterEvents(id)
    })
    import('../stores/fileStore').then(({ useFileStore }) => {
      useFileStore().deleteFilesByMatter(id)
    })
    import('../stores/schedule').then(({ useScheduleStore }) => {
      useScheduleStore().deleteItemsByMatter(id)
    })
    // Clear matter link from sessions (don't delete them — user may still want them)
    import('../stores/chat').then(({ useChatStore }) => {
      const chatStore = useChatStore()
      chatStore.unlinkMatter(id)
    })
  }

  function setActiveMatter(id: string | null) {
    activeMatterId.value = id
  }


  async function seedDemoCase() {
    // ── Wipe stale data ──
    localStorage.removeItem('lawclaw_matters')
    localStorage.removeItem(SEED_FLAG)
    matters.value = []

    const { useTimelineStore } = await import('../stores/timeline')
    const { useFileStore } = await import('../stores/fileStore')
    const tl = useTimelineStore()
    const fs = useFileStore()

    // Clear all reactive state
    tl.events.length = 0
    fs.files.length = 0

    // Clear schedule items linked to matters
    localStorage.removeItem('lawclaw_schedule')
    // Clear IndexedDB files (old records)
    import('../lib/db').then(mod => {
      // Remove all file records via IndexedDB
      mod.getAllFiles().then(files => {
        for (const f of files) mod.deleteFile(f.id).catch(() => {})
      })
    })
    // Clear all timeline events
    import('../lib/db').then(mod => {
      if (typeof (mod as any).getAllTimelineIds === 'function') {
        (mod as any).getAllTimelineIds().then((ids: string[]) => {
          // cleared
        })
      }
    })

    // Block fileStore's async load() from overwriting us
    fs.loaded = true

    seedAllDemoCases(matters, saveMatters, tl, fs)
  }
  function addCategory(matterId: string, category: string) {
    const m = matters.value.find(x => x.id === matterId)
    if (!m) return
    if (!m.customCategories) m.customCategories = []
    if (!m.customCategories.includes(category)) {
      m.customCategories.push(category)
      saveMatters(matters.value)
    }
  }

  function removeCategory(matterId: string, category: string) {
    const m = matters.value.find(x => x.id === matterId)
    if (!m || !m.customCategories) return
    m.customCategories = m.customCategories.filter(c => c !== category)
    saveMatters(matters.value)
  }

  function categoriesForMatter(matterId: string): string[] {
    const m = matters.value.find(x => x.id === matterId)
    const custom = m?.customCategories || []
    return [...new Set(['案件文书', '证据材料', ...custom, '其他'])]
  }

  // ── 多期限管理 ──

  /** 获取案件所有未完成期限（按日期升序） */
  function activeDeadlinesFor(matterId: string): DeadlineItem[] {
    const m = matters.value.find(x => x.id === matterId)
    return getActiveDeadlines(m?.deadlines)
  }

  /** 获取案件最近期限 */
  function nearestDeadlineFor(matterId: string): DeadlineItem | null {
    const m = matters.value.find(x => x.id === matterId)
    return getNearestDeadline(m?.deadlines)
  }

  /** 添加期限 */
  function addDeadline(matterId: string, deadline: Omit<DeadlineItem, 'id' | 'createdAt'>): boolean {
    const m = matters.value.find(x => x.id === matterId)
    if (!m) return false
    if (!m.deadlines) m.deadlines = []
    const now = new Date().toISOString()
    const newDl: DeadlineItem = {
      ...deadline,
      id: generateDeadlineId(),
      createdAt: now,
      // 双时间线：新版本从现在生效，历史为空
      validFrom: now,
      supersededAt: null,
      history: [],
    }
    m.deadlines.push(newDl)
    m.updatedAt = new Date()
    saveMatters(matters.value)

    // 注册 Tauri 通知调度
    _scheduleDeadlineNotification(matterId, newDl, m.title)
    return true
  }

  /** 更新期限（双时间线：实质性修改保留旧版本到 history，可回溯"当时为什么这么安排"） */
  function updateDeadline(
    matterId: string, deadlineId: string,
    updates: Partial<DeadlineItem>, changeReason?: string,
  ): boolean {
    const m = matters.value.find(x => x.id === matterId)
    if (!m || !m.deadlines) return false
    const cur = m.deadlines.find(d => d.id === deadlineId)
    if (!cur) return false
    const now = new Date().toISOString()

    // 实质性字段变更（type/日期/备注/自定义标签）才算修订；completed 翻转不算
    const meaningful = (['type', 'customLabel', 'date', 'note'] as const)
      .some(k => updates[k] !== undefined && updates[k] !== cur[k])
    if (meaningful) {
      cur.history = cur.history || []
      // 旧版本关窗：validUntil = 现在
      cur.history.unshift({
        type: cur.type,
        customLabel: cur.customLabel,
        date: cur.date,
        note: cur.note,
        validFrom: cur.validFrom || cur.createdAt,
        validUntil: now,
        changeReason,
      })
    }
    Object.assign(cur, updates)
    if (meaningful) cur.validFrom = now
    cur.supersededAt = null   // 编辑现行期限 = 开新版本，保持有效
    m.updatedAt = new Date()
    saveMatters(matters.value)

    // 日期变更时重新调度通知
    if (updates.date || updates.completed !== undefined) {
      _scheduleDeadlineNotification(matterId, cur, m.title)
    }
    return true
  }

  /** 撤销期限（软删除：关闭有效期窗口，可追溯、可恢复） */
  function removeDeadline(matterId: string, deadlineId: string, changeReason?: string): boolean {
    const m = matters.value.find(x => x.id === matterId)
    if (!m || !m.deadlines) return false
    const d = m.deadlines.find(x => x.id === deadlineId)
    if (!d || d.supersededAt) return false
    const now = new Date().toISOString()
    d.history = d.history || []
    d.history.unshift({
      type: d.type, customLabel: d.customLabel, date: d.date, note: d.note,
      validFrom: d.validFrom || d.createdAt, validUntil: now, changeReason,
    })
    d.supersededAt = now
    m.updatedAt = new Date()
    saveMatters(matters.value)

    // 取消已注册的通知
    import('../lib/notification').then(({ cancelDeadlineReminders }) => {
      cancelDeadlineReminders(matterId, deadlineId)
    })
    return true
  }

  /** 恢复已撤销的期限（把关闭的有效窗口重新打开，历史保留） */
  function restoreDeadline(matterId: string, deadlineId: string): boolean {
    const m = matters.value.find(x => x.id === matterId)
    if (!m || !m.deadlines) return false
    const d = m.deadlines.find(x => x.id === deadlineId)
    if (!d || !d.supersededAt) return false
    const now = new Date().toISOString()
    d.supersededAt = null
    d.validFrom = now   // 恢复 = 新版本起点（原窗口历史仍在 history 中）
    m.updatedAt = new Date()
    saveMatters(matters.value)
    _scheduleDeadlineNotification(matterId, d, m.title)
    return true
  }

  /** 切换期限完成状态 */
  function toggleDeadline(matterId: string, deadlineId: string): boolean {
    const m = matters.value.find(x => x.id === matterId)
    if (!m || !m.deadlines) return false
    const d = m.deadlines.find(x => x.id === deadlineId)
    if (!d) return false
    d.completed = !d.completed
    m.updatedAt = new Date()
    saveMatters(matters.value)

    // 完成时取消通知，未完成时重新注册
    _scheduleDeadlineNotification(matterId, d, m.title)
    return true
  }

  /** 内部：调度期限通知（异步，不阻塞主流程） */
  function _scheduleDeadlineNotification(matterId: string, deadline: DeadlineItem, matterTitle: string) {
    import('../lib/notification').then(async ({ scheduleDeadlineReminders, cancelDeadlineReminders }) => {
      // 先取消旧提醒
      await cancelDeadlineReminders(matterId, deadline.id)
      // 已完成的期限不提醒
      if (deadline.completed) return
      // 注册新提醒
      import('../lib/caseConstants').then(({ DEADLINE_TYPE_LABELS }) => {
        const label = deadline.customLabel || DEADLINE_TYPE_LABELS[deadline.type] || '期限'
        scheduleDeadlineReminders(
          matterId,
          deadline.id,
          new Date(deadline.date),
          label,
          matterTitle,
        )
      })
    })
  }

  /**
   * 利益冲突检查（新建/编辑案件前调用）
   *
   * 检查规则（依据《律师法》第39条、《律师执业行为规范》第48条）：
   * - **blocked（利益冲突，禁止代理）**：
   *   1. 委托人 = 某现有案件的对方当事人（same-client-as-counterparty）
   *   2. 对方当事人 = 某现有案件的委托人（same-counterparty-as-client）
   * - **warning（潜在冲突，需律师确认）**：
   *   3. 对方律师在现有案件中是己方委托人（same-opposing-counsel）
   *   4. 与现有案件的对方当事人相同（same-counterparty，非冲突但提示）
   * 注：同一委托人出现在多个案件中属于正常代理（同一客户的多起案件），
   *     不构成冲突；真正"对立立场"场景已由规则 1/2 覆盖（客户成为他案对方当事人）。
   *
   * @param client        当前案件委托人
   * @param counterparty  当前案件对方当事人
   * @param opposingCounsel 当前案件对方律师
   * @param excludeMatterId 编辑时排除自身案件 ID
   * @returns 冲突列表（空数组表示无冲突）
   */
  function checkConflict(
    client: string,
    counterparty?: string,
    opposingCounsel?: string,
    excludeMatterId?: string,
  ): ConflictMatch[] {
    const matches: ConflictMatch[] = []
    if (!client) return matches

    for (const m of matters.value) {
      // 编辑时排除自身
      if (excludeMatterId && m.id === excludeMatterId) continue
      // 已归档案件不参与冲突检查（已结束，无利益冲突风险）
      if (m.stage === '已归档') continue

      // 规则1: 当前委托人 = 某现有案件的对方当事人 → blocked
      if (m.counterparty && isPartyMatch(client, m.counterparty)) {
        matches.push({
          level: 'blocked', type: 'same-client-as-counterparty',
          description: `当前委托人「${client}」与案件「${m.title}」的对方当事人「${m.counterparty}」相同。律师不得在同一案件中为双方当事人担任代理人，亦不得在后续案件中为前案对方当事人代理针对前案委托人的事务。`,
          matterId: m.id, matterTitle: m.title, matterStage: m.stage,
          field: 'client', matchedValue: m.counterparty,
        })
      }

      // 规则2: 当前对方当事人 = 某现有案件的委托人 → blocked
      if (counterparty && m.client && isPartyMatch(counterparty, m.client)) {
        matches.push({
          level: 'blocked', type: 'same-counterparty-as-client',
          description: `当前对方当事人「${counterparty}」是案件「${m.title}」的现有委托人「${m.client}」。代理该对方当事人将构成对现有委托人利益冲突。`,
          matterId: m.id, matterTitle: m.title, matterStage: m.stage,
          field: 'counterparty', matchedValue: m.client,
        })
      }

      // 规则3（原规则4）: 对方律师在现有案件中是己方委托人 → warning
      if (opposingCounsel && m.client && isPartyMatch(opposingCounsel, m.client)) {
        matches.push({
          level: 'warning', type: 'same-opposing-counsel',
          description: `对方律师「${opposingCounsel}」是案件「${m.title}」的现有委托人。律师作为委托人将构成执业行为规范上的潜在冲突。`,
          matterId: m.id, matterTitle: m.title, matterStage: m.stage,
          field: 'opposingCounsel', matchedValue: m.client,
        })
      }

      // 规则4（原规则5）: 与现有案件的对方当事人相同 → warning（非冲突但提示，可能是系列案件）
      if (counterparty && m.counterparty && isPartyMatch(counterparty, m.counterparty)) {
        // 仅当委托人不同时才提示（委托人相同即同一客户系列案件，正常代理）
        if (!m.client || !isPartyMatch(client, m.client)) {
          matches.push({
            level: 'warning', type: 'same-counterparty',
            description: `对方当事人「${counterparty}」与案件「${m.title}」的对方当事人相同。可能是系列案件，请律师核实是否构成关联案件合并审理。`,
            matterId: m.id, matterTitle: m.title, matterStage: m.stage,
            field: 'counterparty', matchedValue: m.counterparty,
          })
        }
      }
    }

    return matches
  }

  /** 获取冲突的最高级别 */
  function getConflictLevel(matches: ConflictMatch[]): ConflictLevel {
    if (matches.some(m => m.level === 'blocked')) return 'blocked'
    if (matches.some(m => m.level === 'warning')) return 'warning'
    return 'none'
  }

  return {
    matters, activeMatterId, activeMatter, activeMatters, archivedMatters, mattersByStage,
    addMatter, updateMatter, deleteMatter, setActiveMatter, seedDemoCase,
    addCategory, removeCategory, categoriesForMatter, STAGES,
    checkConflict, getConflictLevel,
    activeDeadlinesFor, nearestDeadlineFor, addDeadline, updateDeadline, removeDeadline, restoreDeadline, toggleDeadline,
  }
})

