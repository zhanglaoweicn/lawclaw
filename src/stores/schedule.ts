import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ScheduleItem, ScheduleType } from '../types/legal'
import { useMatterStore } from './matter'
import {
  scheduleDeadlineReminders,
  cancelDeadlineReminders,
  rescheduleMatterDeadlineReminders,
  requestNotificationPermission,
  isNotificationGranted,
} from '../lib/notification'
import { DEADLINE_TYPE_LABELS } from '../lib/caseConstants'

interface ScheduleTemplate {
  id: string
  name: string
  icon: string
  description: string
  items: Array<{
    title: string
    type: ScheduleType
    durationMinutes: number
    note?: string
    offsetDays?: number
  }>
}

const STORAGE_KEY = 'lawclaw_schedule'

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

function loadItems(): ScheduleItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { return [] }
  // ── Auto-seed demo data if empty ──
  // 基准 = 今天 00:00（相对日期：d=0 即今天，负数为过去；h 为当天钟点而非偏移，
  // 保证 t(0,16,30) = 今天 16:30 而不是次日凌晨）
  const base = new Date(); base.setHours(0, 0, 0, 0)
  const D = 86400000, H = 3600000
  const t = (d: number, h: number, m = 0) => new Date(+base + d * D + h * H + m * 60000).toISOString()
  const demo: ScheduleItem[] = [
    { id: generateId(), title: '与张伟案当事人会见', dateTime: t(0,9,0), endDateTime: t(0,10,30), type: 'meeting', completed: false, note: '讨论赔偿方案', createdAt: t(-3,14) },
    { id: generateId(), title: '提交陈芳案代理词', dateTime: t(0,12,0), type: 'deadline', completed: false, note: '劳动仲裁案', createdAt: t(-5,9) },
    { id: generateId(), title: '东城区法院调取证据', dateTime: t(0,14,0), endDateTime: t(0,16,0), type: 'appointment', completed: false, note: '工商登记信息', createdAt: t(-2,10) },
    { id: generateId(), title: '团队案件讨论会', dateTime: t(0,16,30), endDateTime: t(0,17,30), type: 'meeting', completed: false, createdAt: t(-1,9) },
    { id: generateId(), title: '李梅房产继承案调解', dateTime: t(1,9,30), endDateTime: t(1,11,0), type: 'court', completed: false, note: '朝阳区法院', createdAt: t(-10,11) },
    { id: generateId(), title: '刘洋案二审上诉状截止', dateTime: t(2,17,0), type: 'deadline', completed: false, note: '最后一天', createdAt: t(-20,10) },
    { id: generateId(), title: '律所合伙人会议', dateTime: t(3,10,0), endDateTime: t(3,12,0), type: 'meeting', completed: false, createdAt: t(-14,9) },
    { id: generateId(), title: '宋氏继承纠纷案开庭', dateTime: t(3,14,0), endDateTime: t(3,17,0), type: 'court', completed: false, note: '西城区法院', createdAt: t(-30,9) },
    { id: generateId(), title: '整理下周开庭材料', dateTime: t(4,14,0), endDateTime: t(4,18,0), type: 'personal', completed: false, createdAt: t(-2,11) },
    { id: generateId(), title: '林达公司买卖合同纠纷开庭', dateTime: t(6,9,0), endDateTime: t(6,12,0), type: 'court', completed: false, note: '深圳南山区法院', createdAt: t(-25,14) },
    { id: generateId(), title: '顾问单位华兴科技回访', dateTime: t(8,9,30), endDateTime: t(8,11,30), type: 'meeting', completed: false, createdAt: t(-5,11) },
    { id: generateId(), title: '建设工程合同纠纷鉴定质证', dateTime: t(18,9,0), endDateTime: t(18,12,0), type: 'court', completed: false, note: '丰台区法院', createdAt: t(-30,10) },
    { id: generateId(), title: '律所团建——怀柔青龙湖', dateTime: t(19,8,0), endDateTime: t(19,18,0), type: 'personal', completed: false, createdAt: t(-14,9) },
    { id: generateId(), title: '陈某某受贿罪一审开庭', dateTime: t(24,9,0), endDateTime: t(24,17,0), type: 'court', completed: false, note: '北京市一中院', createdAt: t(-40,9) },
    { id: generateId(), title: '赵某欠款纠纷案开庭', dateTime: t(-2,9,0), endDateTime: t(-2,11,0), type: 'court', completed: true, createdAt: t(-20,10) },
    { id: generateId(), title: '提交管辖权异议申请书', dateTime: t(-3,17,0), type: 'deadline', completed: true, createdAt: t(-10,9) },
    { id: generateId(), title: '新人合同审查培训', dateTime: t(-5,10,0), endDateTime: t(-5,12,0), type: 'meeting', completed: true, createdAt: t(-12,9) },
    { id: generateId(), title: '年度体检', dateTime: t(-7,8,0), endDateTime: t(-7,12,0), type: 'personal', completed: true, createdAt: t(-30,9) },
  ]
  saveItems(demo)
  return demo
}

function saveItems(items: ScheduleItem[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export const useScheduleStore = defineStore('schedule', () => {
  const items = ref<ScheduleItem[]>(loadItems())
  const syncedCourtKeys = ref<Set<string>>(new Set())
  const syncedDeadlineKeys = ref<Set<string>>(new Set())

  const showCompleted = ref(false)
  const lastUsedType = ref<ScheduleType>('meeting')
  // 通知权限状态
  const notificationEnabled = ref(false)
  function toggleShowCompleted() {
    showCompleted.value = !showCompleted.value
  }
  function setLastUsedType(t: ScheduleType) {
    lastUsedType.value = t
  }

  // ── Tauri 通知集成 ──
  // 应用启动时检查权限状态
  async function checkNotificationStatus() {
    notificationEnabled.value = await isNotificationGranted()
    return notificationEnabled.value
  }

  // 请求权限并初始化
  async function enableNotifications() {
    const granted = await requestNotificationPermission()
    notificationEnabled.value = granted
    if (granted) {
      // 重新调度所有未完成期限的通知
      await rescheduleAllDeadlineReminders()
    }
    return granted
  }

  // 为所有案件的未完成期限重新注册提醒
  async function rescheduleAllDeadlineReminders() {
    if (!notificationEnabled.value) return
    const ms = useMatterStore()
    for (const matter of ms.matters) {
      if (!matter.deadlines || matter.deadlines.length === 0) continue
      await rescheduleMatterDeadlineReminders(
        matter.id,
        matter.deadlines
          .filter(d => !d.supersededAt)   // 已撤销期限不再提醒
          .map(d => ({
          id: d.id,
          date: d.date,
          type: d.type,
          customLabel: d.customLabel,
          completed: !!d.completed,
        })),
        matter.title,
        DEADLINE_TYPE_LABELS,
      )
    }
  }

/**
 * 把「某日」类日程（开庭/期限）统一到本地 HH:00。
 *
 * 开庭与期限在实务上都是"某日"概念。数据源可能是 date-only（手填）也可能是带钟点的
 * 时间戳（种子/表单产生的 Date）——后者若原样使用，日历会显示成"9月21日 04:13"，
 * 通知也会在凌晨触发。此函数按当地日历日重建，两类输入统一落到 hour 点。
 */
function normalizeDayDateTime(value: string, hour = 9): string {
  let y: number, mo: number, dd: number
  const plain = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (plain) {
    y = Number(plain[1]); mo = Number(plain[2]); dd = Number(plain[3])
  } else {
    const d = new Date(value)
    if (isNaN(d.getTime())) return value
    y = d.getFullYear(); mo = d.getMonth() + 1; dd = d.getDate()
  }
  const local = new Date(y, mo - 1, dd, hour, 0, 0)
  return isNaN(local.getTime()) ? value : local.toISOString()
}

/** 开庭日 → 本地 09:00（开庭惯例时段） */
function normalizeCourtDateTime(courtDate: string): string {
  return normalizeDayDateTime(courtDate, 9)
}

  // ── Conflict detection ──
  function checkCourtConflicts(dateTime: string, endDateTime?: string, excludeId?: string): ScheduleItem[] {
    const newStart = new Date(dateTime)
    const newEnd = endDateTime ? new Date(endDateTime) : new Date(newStart.getTime() + 3600000)
    return items.value.filter(item => {
      if (item.id === excludeId) return false
      if (item.type !== 'court') return false
      const existingStart = new Date(item.dateTime)
      // date-only 开庭（无结束时间且为零点）：按"同日即冲突"处理，避免小时窗口错开导致漏报
      if (!item.endDateTime && /T00:00(?::00)?(\.\d+)?Z?$/.test(item.dateTime)) {
        const dayStart = new Date(existingStart.getFullYear(), existingStart.getMonth(), existingStart.getDate())
        const dayEnd = new Date(dayStart.getTime() + 86400000)
        return newStart < dayEnd && newEnd > dayStart
      }
      const existingEnd = item.endDateTime ? new Date(item.endDateTime) : new Date(existingStart.getTime() + 3600000)
      return newStart < existingEnd && newEnd > existingStart
    })
  }

  // ── Auto-sync from matters ──
  function syncFromMatters() {
    const ms = useMatterStore()

    // Remove stale synced items (matter deleted or source removed)
    const staleIds: string[] = []
    for (const item of items.value) {
      if (item.id?.startsWith('deadline-')) {
        // v2 旧版单期限模型已退役：deadlines[] 的 dl-{id} 项已覆盖其内容
        staleIds.push(item.id)
        continue
      }
      if (!item.id?.startsWith('court-') && !item.id?.startsWith('dl-')) continue
      const matterId = item.id.replace(/^(court-|dl-)/, '')
      const matter = ms.matters.find(m => m.id === matterId)
      if (!matter) {
        staleIds.push(item.id)
      } else if (item.id.startsWith('court-') && !matter.courtDate) {
        staleIds.push(item.id)
      } else if (item.id.startsWith('dl-')) {
        // 对应期限已被撤销/完成/删除 → 日程项过期
        const dlId = item.id.slice(3)
        const dl = (matter.deadlines || []).find(d => d.id === dlId)
        if (!dl || dl.supersededAt || dl.completed) staleIds.push(item.id)
      }
    }
    if (staleIds.length > 0) {
      items.value = items.value.filter(i => !staleIds.includes(i.id))
      staleIds.forEach(id => { syncedCourtKeys.value.delete(id); syncedDeadlineKeys.value.delete(id) })
    }

    // Sync: update existing OR create new
    for (const m of ms.matters) {
      const courtKey = `court-${m.id}`
      if (m.courtDate) {
        const existing = items.value.find(i => i.id === courtKey)
        if (existing) {
          const newDate = normalizeCourtDateTime(m.courtDate)
          if (existing.dateTime !== newDate) { existing.dateTime = newDate }
        } else if (!syncedCourtKeys.value.has(courtKey)) {
          items.value.unshift({
            id: courtKey, title: `开庭: ${m.title}`,
            dateTime: normalizeCourtDateTime(m.courtDate),
            type: 'court', matterId: m.id, completed: false,
            createdAt: new Date().toISOString(),
          })
        }
        syncedCourtKeys.value.add(courtKey)
      }

      // ── 多期限模型（v3+）：每个现行有效且未完成的期限各同步一条日程 ──
      for (const dl of (m.deadlines || [])) {
        if (dl.supersededAt || dl.completed) continue
        const dlKey = `dl-${dl.id}`
        const label = dl.customLabel || DEADLINE_TYPE_LABELS[dl.type] || '期限'
        const iso = normalizeDayDateTime(dl.date)
        const existing = items.value.find(i => i.id === dlKey)
        if (existing) {
          if (existing.dateTime !== iso) { existing.dateTime = iso }
          if (existing.title !== `${label}: ${m.title}`) { existing.title = `${label}: ${m.title}` }
        } else if (!syncedDeadlineKeys.value.has(dlKey)) {
          items.value.unshift({
            id: dlKey, title: `${label}: ${m.title}`,
            dateTime: iso,
            type: dl.type === 'court-date' ? 'court' : 'deadline',
            matterId: m.id, completed: false,
            createdAt: new Date().toISOString(),
          })
        }
        syncedDeadlineKeys.value.add(dlKey)
      }
    }
    saveItems(items.value)
  }

  /** 按 court-{matterId} 规范键 upsert 开庭日程（与 syncFromMatters 同键，避免重复条目） */
  function ensureCourtItem(matterId: string, matterTitle: string, courtDate: string, note = ''): boolean {
    const key = `court-${matterId}`
    const iso = normalizeCourtDateTime(courtDate)
    const existing = items.value.find(i => i.id === key)
    if (existing) {
      if (existing.dateTime !== iso) { existing.dateTime = iso; saveItems(items.value) }
      return false
    }
    items.value.unshift({
      id: key, title: `开庭: ${matterTitle}`,
      dateTime: iso,
      type: 'court', matterId, completed: false,
      note: note || undefined,
      createdAt: new Date().toISOString(),
    })
    saveItems(items.value)
    return true
  }

  // ── CRUD ──
  function addItem(item: Omit<ScheduleItem, 'id' | 'createdAt'>): ScheduleItem {
    const newItem: ScheduleItem = {
      ...item,
      id: generateId(),
      createdAt: new Date().toISOString(),
    }
    items.value.unshift(newItem)
    saveItems(items.value)
    return newItem
  }

  function updateItem(id: string, updates: Partial<ScheduleItem>) {
    const idx = items.value.findIndex(i => i.id === id)
    if (idx === -1) return
    items.value[idx] = { ...items.value[idx], ...updates }
    saveItems(items.value)
  }

  function deleteItem(id: string) {
    items.value = items.value.filter(i => i.id !== id)
    saveItems(items.value)
  }

  function toggleComplete(id: string) {
    const item = items.value.find(i => i.id === id)
    if (item) {
      item.completed = !item.completed
      saveItems(items.value)
    }
  }

  function deleteItemsByMatter(matterId: string) {
    items.value = items.value.filter(i => i.matterId !== matterId)
    saveItems(items.value)
  }

  // ── Schedule Templates ──
  const scheduleTemplates: ScheduleTemplate[] = [
    {
      id: 'court-prep', name: '开庭准备', icon: '⚡',
      description: '开庭前后关键节点',
      items: [
        { title: '庭前策略讨论会', type: 'meeting', durationMinutes: 120, offsetDays: -3 },
        { title: '证据最终核对', type: 'appointment', durationMinutes: 60, offsetDays: -1 },
        { title: '开庭', type: 'court', durationMinutes: 240, offsetDays: 0, note: '携带全部证据原件及代理手续' },
        { title: '庭后复盘及补充代理意见', type: 'meeting', durationMinutes: 90, offsetDays: 1 },
      ],
    },
    {
      id: 'client-meeting', name: '客户案件沟通', icon: '🤝',
      description: '客户会见及案件梳理',
      items: [
        { title: '客户会见 — 案情梳理', type: 'meeting', durationMinutes: 120, offsetDays: 0 },
        { title: '内部案件分析会', type: 'meeting', durationMinutes: 60, offsetDays: 1 },
        { title: '出具初步法律意见', type: 'deadline', durationMinutes: 0, offsetDays: 3, note: '向客户发送初步法律分析意见' },
      ],
    },
    {
      id: 'evidence-collection', name: '证据收集', icon: '📋',
      description: '调证、质证关键日程',
      items: [
        { title: '赴法院/机构调取证据', type: 'appointment', durationMinutes: 180, offsetDays: 0 },
        { title: '证据材料梳理归类', type: 'meeting', durationMinutes: 120, offsetDays: 1 },
        { title: '证据交换截止', type: 'deadline', durationMinutes: 0, offsetDays: 5 },
      ],
    },
    {
      id: 'appeal', name: '上诉流程', icon: '🔄',
      description: '收到判决/裁定后的上诉日程（自送达之日起算）',
      items: [
        { title: '研读一审裁判文书并分析', type: 'meeting', durationMinutes: 120, offsetDays: 0, note: '识别是判决书还是裁定书，分别适用15日或10日上诉期' },
        { title: '与客户沟通上诉意向', type: 'meeting', durationMinutes: 60, offsetDays: 1, note: '告知上诉风险、费用、审限，确认是否上诉' },
        { title: '起草上诉状', type: 'meeting', durationMinutes: 180, offsetDays: 3 },
        { title: '客户确认上诉状并签字', type: 'deadline', durationMinutes: 0, offsetDays: 7, note: '需预留邮寄/当面签署时间' },
        { title: '递交上诉状 + 缴纳上诉费', type: 'deadline', durationMinutes: 0, offsetDays: 10, note: '通过原审法院递交；上诉费按上诉请求金额计算' },
        { title: '裁定上诉截止日（10日）', type: 'deadline', durationMinutes: 0, offsetDays: 10, note: '《民事诉讼法》第171条：不予受理、管辖权异议、驳回起诉裁定上诉期为10日' },
        { title: '判决上诉截止日（15日）', type: 'deadline', durationMinutes: 0, offsetDays: 15, note: '《民事诉讼法》第171条：一审判决上诉期为15日，自送达之日起算' },
      ],
    },
  ]

  function applyTemplate(templateId: string, startDate: string, matterId?: string): ScheduleItem[] {
    const template = scheduleTemplates.find(t => t.id === templateId)
    if (!template) return []
    const baseDate = new Date(startDate)
    const created: ScheduleItem[] = []
    for (const tpl of template.items) {
      const date = new Date(baseDate)
      if (tpl.offsetDays) date.setDate(date.getDate() + tpl.offsetDays)
      const dateTime = date.toISOString().replace(':00.000Z', ':00')
      const endDateTime = tpl.durationMinutes > 0
        ? new Date(date.getTime() + tpl.durationMinutes * 60000).toISOString().replace(':00.000Z', ':00')
        : undefined
      const newItem = {
        id: generateId(),
        title: tpl.title, type: tpl.type,
        dateTime, endDateTime,
        completed: false, matterId: matterId, note: tpl.note,
        createdAt: new Date().toISOString(),
      }
      items.value.unshift(newItem)
      created.push(newItem)
    }
    saveItems(items.value)
    return created
  }

  // ── Getters ──
  const sortedItems = computed(() =>
    [...items.value].sort((a, b) => new Date(a.dateTime).getTime() - new Date(b.dateTime).getTime())
  )

  return {
    items, sortedItems, showCompleted, lastUsedType, scheduleTemplates,
    notificationEnabled,
    syncFromMatters, ensureCourtItem, addItem, updateItem, deleteItem, toggleComplete, deleteItemsByMatter,
    toggleShowCompleted, checkCourtConflicts, applyTemplate, setLastUsedType,
    checkNotificationStatus, enableNotifications, rescheduleAllDeadlineReminders,
  }
})
