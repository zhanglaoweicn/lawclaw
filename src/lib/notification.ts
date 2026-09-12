/**
 * Tauri 通知服务 —— 期限提醒本地推送
 *
 * 设计要点：
 * 1. 通过 @tauri-apps/api 调用 Rust 层命令
 * 2. 不依赖后端 WebSocket —— 即使后端关闭，已注册的定时通知仍能触发
 * 3. 提醒策略：期限前 7 日 / 3 日 / 1 日 / 当日 四档预警
 * 4. 律师可自定义提醒时间（如每天 9:00 推送当日待办）
 *
 * 注意：在 dev 模式下（vite dev server，非 Tauri 环境）调用会降级为
 * Notification API（浏览器原生通知），不影响开发调试。
 */

import { invoke, isTauri } from '@tauri-apps/api/core'

export interface ScheduledNotification {
  id: string
  fire_at_unix: number
  title: string
  body: string
  matter_id?: string
}

export type ReminderOffset = 7 | 3 | 1 | 0  // 天数：7/3/1/0（当日）

export interface DeadlineReminderConfig {
  /** 期限前几日提醒（默认 [7, 3, 1, 0]） */
  offsets: ReminderOffset[]
  /** 当日提醒的具体时间（24h 制，默认 09:00） */
  dailyHour: number
  /** 非当日提醒的触发时间（默认 09:00） */
  reminderHour: number
}

const DEFAULT_CONFIG: DeadlineReminderConfig = {
  offsets: [7, 3, 1, 0],
  dailyHour: 9,
  reminderHour: 9,
}

/**
 * 请求通知权限
 * Windows 10/11 首次调用会触发系统授权弹窗
 */
export async function requestNotificationPermission(): Promise<boolean> {
  if (isTauri()) {
    try {
      return await invoke<boolean>('request_notification_permission')
    } catch (e) {
      console.warn('[通知] Tauri 权限请求失败:', e)
      return false
    }
  }
  // 浏览器降级：使用 Notification API
  if ('Notification' in window) {
    const result = await Notification.requestPermission()
    return result === 'granted'
  }
  return false
}

/**
 * 检查通知权限是否已授予
 */
export async function isNotificationGranted(): Promise<boolean> {
  if (isTauri()) {
    try {
      const { isPermissionGranted } = await import('@tauri-apps/plugin-notification')
      return await isPermissionGranted()
    } catch {
      return false
    }
  }
  return 'Notification' in window && Notification.permission === 'granted'
}

/**
 * 立即发送一条通知（用于测试或即时提醒）
 */
export async function sendNotification(title: string, body: string): Promise<void> {
  if (isTauri()) {
    try {
      await invoke('send_notification', { title, body })
    } catch (e) {
      console.warn('[通知] 发送失败:', e)
    }
    return
  }
  // 浏览器降级
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, { body })
  }
}

/**
 * 安排一条定时通知
 *
 * @param id 唯一 ID（建议格式：`deadline-{matterId}-{deadlineId}-{offset}d`）
 * @param fireAt 触发时间（Date 对象）
 * @param title 通知标题
 * @param body 通知正文
 * @param matterId 关联案件 ID（可选，用于点击跳转）
 */
export async function scheduleNotification(
  id: string,
  fireAt: Date,
  title: string,
  body: string,
  matterId?: string,
): Promise<void> {
  const fireAtUnix = Math.floor(fireAt.getTime() / 1000)

  if (isTauri()) {
    try {
      await invoke('schedule_notification', {
        id,
        fire_at_unix: fireAtUnix,
        title,
        body,
        matter_id: matterId || null,
      })
    } catch (e) {
      console.warn('[通知] 定时安排失败:', e)
    }
    return
  }
  // 浏览器降级：用 setTimeout 模拟（仅当前会话有效）
  const delay = fireAt.getTime() - Date.now()
  if (delay > 0 && delay < 2147483647) {
    setTimeout(() => sendNotification(title, body), delay)
  }
}

/**
 * 取消已安排的通知
 */
export async function cancelNotification(id: string): Promise<void> {
  if (isTauri()) {
    try {
      await invoke('cancel_notification', { id })
    } catch (e) {
      console.warn('[通知] 取消失败:', e)
    }
  }
  // 浏览器降级：无法取消 setTimeout（生产环境用 Tauri）
}

/**
 * 列出所有待触发的通知
 */
export async function listScheduledNotifications(): Promise<ScheduledNotification[]> {
  if (isTauri()) {
    try {
      return await invoke<ScheduledNotification[]>('list_scheduled_notifications')
    } catch {
      return []
    }
  }
  return []
}

// ─────────────────────────────────────────────
//  期限提醒专用调度逻辑
// ─────────────────────────────────────────────

/**
 * 为一个期限安排多档提醒
 *
 * @param matterId 案件 ID
 * @param deadlineId 期限 ID
 * @param deadlineDate 期限日期
 * @param deadlineLabel 期限标签（如"举证期限"、"判决上诉期"）
 * @param matterTitle 案件标题
 * @param config 提醒配置
 * @returns 已注册的通知 ID 列表
 */
export async function scheduleDeadlineReminders(
  matterId: string,
  deadlineId: string,
  deadlineDate: Date,
  deadlineLabel: string,
  matterTitle: string,
  config: Partial<DeadlineReminderConfig> = {},
): Promise<string[]> {
  const cfg = { ...DEFAULT_CONFIG, ...config }
  const registeredIds: string[] = []
  const now = new Date()

  for (const offset of cfg.offsets) {
    // 计算提醒触发时间
    const fireAt = new Date(deadlineDate)
    fireAt.setDate(fireAt.getDate() - offset)
    fireAt.setHours(offset === 0 ? cfg.dailyHour : cfg.reminderHour, 0, 0, 0)

    // 跳过已过去的时间
    if (fireAt <= now) continue

    const id = `deadline-${matterId}-${deadlineId}-${offset}d`
    let title: string
    let body: string

    if (offset === 0) {
      title = `⏰ 今日截止：${deadlineLabel}`
      body = `案件「${matterTitle}」的${deadlineLabel}今日到期，请立即处理。`
    } else if (offset === 1) {
      title = `🔴 明日截止：${deadlineLabel}`
      body = `案件「${matterTitle}」的${deadlineLabel}将于明日到期，请今日完成相关准备。`
    } else if (offset === 3) {
      title = `🟠 3 日内截止：${deadlineLabel}`
      body = `案件「${matterTitle}」的${deadlineLabel}将于 3 日内到期（${formatDate(deadlineDate)}），请安排处理。`
    } else {
      title = `🟡 ${offset} 日后截止：${deadlineLabel}`
      body = `案件「${matterTitle}」的${deadlineLabel}将于 ${offset} 日后到期（${formatDate(deadlineDate)}），请关注进度。`
    }

    await scheduleNotification(id, fireAt, title, body, matterId)
    registeredIds.push(id)
  }

  return registeredIds
}

/**
 * 取消一个期限的所有提醒
 */
export async function cancelDeadlineReminders(
  matterId: string,
  deadlineId: string,
  offsets: ReminderOffset[] = [7, 3, 1, 0],
): Promise<void> {
  for (const offset of offsets) {
    const id = `deadline-${matterId}-${deadlineId}-${offset}d`
    await cancelNotification(id)
  }
}

/**
 * 为一个案件的所有期限重新计算提醒
 * 用于案件加载时批量注册
 */
export async function rescheduleMatterDeadlineReminders(
  matterId: string,
  deadlines: Array<{ id: string; date: string; type: string; customLabel?: string; completed: boolean }>,
  matterTitle: string,
  deadlineTypeLabels?: Record<string, string>,
): Promise<void> {
  for (const dl of deadlines) {
    // 已完成的期限不提醒
    if (dl.completed) continue

    // 先取消旧提醒
    await cancelDeadlineReminders(matterId, dl.id)

    // 重新注册
    const label = dl.customLabel || deadlineTypeLabels?.[dl.type] || '期限'
    await scheduleDeadlineReminders(
      matterId,
      dl.id,
      new Date(dl.date),
      label,
      matterTitle,
    )
  }
}

function formatDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
