/**
 * 统一剪贴板写入：Clipboard API 失败时降级 execCommand。
 *
 * navigator.clipboard.writeText 在文档失焦（如自动化合成点击）或 WebView
 * 权限策略下会抛 NotAllowedError；隐藏 textarea + execCommand('copy') 是
 * 兼容性最好的降级路径。
 */

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // fall through to legacy path
  }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.top = '-1000px'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}
