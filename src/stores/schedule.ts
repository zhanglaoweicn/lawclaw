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
  // 首启为空日程：本产品不带任何内置数据，日程由案件期限/开庭日同步或律师手工创建
  return []
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
