/**
 * ics.ts — 把日程/期限导出为 iCalendar (.ics)，可一键导入手机日历或 Outlook。
 *
 * 设计说明：
 * - 时间用 UTC（Z 后缀）本地时间转换，兼容性最好（Apple/Google/Outlook 均支持）
 * - 无结束时间的条目（如"截止期限"）按 1 小时日历块处理
 * - 已完成条目仍导出（日历中保留痕迹），通过 CATEGORIES 标注类型
 */

export interface IcsEventInput {
  title: string
  dateTime: string | Date
  endDateTime?: string | Date | null
  type?: string          // court | meeting | deadline | appointment | personal
  note?: string
  completed?: boolean
}

const TYPE_LABELS: Record<string, string> = {
  court: '开庭',
  meeting: '会议/会见',
  deadline: '截止期限',
  appointment: '约见/调证',
  personal: '个人',
}

function pad(n: number): string {
  return n < 10 ? '0' + n : String(n)
}

/** Date → iCal UTC 格式：YYYYMMDDTHHMMSSZ */
function icsDate(d: Date): string {
  return (
    d.getUTCFullYear() + pad(d.getUTCMonth() + 1) + pad(d.getUTCDate()) +
    'T' + pad(d.getUTCHours()) + pad(d.getUTCMinutes()) + pad(d.getUTCSeconds()) + 'Z'
  )
}

/** 按 RFC 5545 转义文本特殊字符 */
function esc(s: string): string {
  return (s || '')
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\r?\n/g, '\\n')
}

/** 折行：RFC 规定单行最长 75 字节，这里按 64 字符保守折叠（CRLF + 空格续行） */
function foldLine(line: string): string {
  if (line.length <= 64) return line
  const parts: string[] = []
  let rest = line
  parts.push(rest.slice(0, 64))
  rest = rest.slice(64)
  while (rest.length > 0) {
    parts.push(' ' + rest.slice(0, 72))
    rest = rest.slice(72)
  }
  return parts.join('\r\n')
}

export function buildIcs(events: IcsEventInput[], calendarName = 'LawClaw 律师日程'): string {
  const lines: string[] = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//LawClaw//律师日程//CN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    `X-WR-CALNAME:${esc(calendarName)}`,
  ]
  const now = new Date()
  events.forEach((ev, i) => {
    const start = new Date(ev.dateTime)
    if (isNaN(start.getTime())) return
    const end = ev.endDateTime ? new Date(ev.endDateTime) : new Date(start.getTime() + 3600000)
    const typeLabel = TYPE_LABELS[ev.type || ''] || '日程'
    const summary = ev.completed ? `[已完成] ${ev.title}` : ev.title
    lines.push('BEGIN:VEVENT')
    lines.push(`UID:lawclaw-${now.getTime()}-${i}@lawclaw.app`)
    lines.push(`DTSTAMP:${icsDate(now)}`)
    lines.push(`DTSTART:${icsDate(start)}`)
    lines.push(`DTEND:${icsDate(end)}`)
    lines.push(`SUMMARY:${esc(summary)}`)
    const descParts: string[] = []
    if (ev.type) descParts.push(`类型：${typeLabel}`)
    if (ev.note) descParts.push(esc(ev.note))
    if (descParts.length) lines.push(`DESCRIPTION:${descParts.join('\\n')}`)
    lines.push(`CATEGORIES:${esc(typeLabel)}`)
    if (ev.completed) lines.push('STATUS:CONFIRMED')
    lines.push('END:VEVENT')
  })
  lines.push('END:VCALENDAR')
  return lines.map(foldLine).join('\r\n')
}

/** 触发浏览器下载 .ics 文件 */
export function downloadIcs(content: string, filename: string): void {
  const blob = new Blob(['\uFEFF' + content], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
