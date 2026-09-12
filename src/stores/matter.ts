import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Matter, MatterStage, DeadlineItem, DeadlineType } from '../types/legal'
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
  // ── 首启为空台账 ──
  // 本产品不带任何内置/测试案件数据：首次启动就是空台账，由律师自行建档。
  // SEED_FLAG 只用于记住"这台机器已经初启过"，避免反复走这里。
  localStorage.setItem(SEED_FLAG, '1')
  return []
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
    addMatter, updateMatter, deleteMatter, setActiveMatter,
    addCategory, removeCategory, categoriesForMatter, STAGES,
    checkConflict, getConflictLevel,
    activeDeadlinesFor, nearestDeadlineFor, addDeadline, updateDeadline, removeDeadline, restoreDeadline, toggleDeadline,
  }
})

