/**
 * docxExport.ts — Markdown → Word (.docx) 导出助手
 *
 * 走后端 export_docx RPC（python-docx，宋体/黑体法律文书格式），
 * 下载触发与 ics.ts 的 downloadIcs 保持同一模式。
 */

export async function exportMarkdownAsDocx(
  title: string,
  markdown: string,
  matterTitle?: string,
): Promise<void> {
  const { backend } = await import('./backend')
  const r = await backend.exportDocx(title, markdown, matterTitle)
  if (!r.ok || !r.data || !r.filename) {
    throw new Error(r.error || '导出失败')
  }
  const bytes = Uint8Array.from(atob(r.data), c => c.charCodeAt(0))
  const blob = new Blob([bytes], {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = r.filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
