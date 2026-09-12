/**
 * 全局统一的 Markdown 渲染出口：marked（GFM/换行）+ DOMPurify 消毒。
 *
 * LLM 输出、文件内容、检索结果等不可信文本一律经此渲染，
 * 禁止在组件里直接 marked.parse() 后 v-html（存在 HTML 注入风险）。
 */
import DOMPurify from 'dompurify'
import { markRaw } from 'vue'
import { marked } from 'marked'

const renderer = markRaw(new marked.Renderer())
renderer.link = function ({ href, text }) {
  return `<a href="${href}" target="_blank" rel="noopener">${text}</a>`
}
marked.setOptions({ renderer, breaks: true, gfm: true })

/** Markdown → 消毒后的 HTML（渲染失败时按原文本返回） */
export function renderMarkdown(content: string): string {
  try {
    const html = marked.parse(content) as string
    // target="_blank" 默认会被剥离，显式保留
    return DOMPurify.sanitize(html, { ADD_ATTR: ['target'] })
  } catch {
    return content
  }
}
