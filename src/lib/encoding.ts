/**
 * Data URL(base64) ⇄ 文本 的 UTF-8 安全转换
 *
 * 裸用 atob/btoa 处理中文会出问题：
 * - atob 把 UTF-8 多字节序列当 Latin1 单字符返回 → 预览/编辑器里中文乱码
 * - btoa 遇到非 Latin1 字符（中文）直接抛 RangeError，或把乱码写回文件（数据损坏）
 * 统一走 TextDecoder/TextEncoder。
 */

/** 解码 Data URL 为 UTF-8 文本；解码失败返回空串 */
export function dataUrlToText(dataUrl: string): string {
  try {
    const b64 = dataUrl.split(',')[1] || ''
    const bin = atob(b64)
    const bytes = Uint8Array.from(bin, c => c.charCodeAt(0))
    return new TextDecoder('utf-8').decode(bytes)
  } catch {
    return ''
  }
}

/** UTF-8 文本编码为 Data URL（默认 text/plain） */
export function textToDataUrl(text: string, mime = 'text/plain'): string {
  const bytes = new TextEncoder().encode(text)
  let bin = ''
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i])
  return `data:${mime};base64,${btoa(bin)}`
}
