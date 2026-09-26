/**
 * 全局统一的 Markdown 渲染出口：marked（GFM/换行）+ DOMPurify 消毒。
 *
 * LLM 输出、文件内容、检索结果等不可信文本一律经此渲染，
 * 禁止在组件里直接 marked.parse() 后 v-html（存在 HTML 注入风险）；
 * 也不允许在消毒之后再拼接未转义字符串（SkillPage「数据来源」的教训）。
 */
import DOMPurify from 'dompurify'
import { markRaw } from 'vue'
import { marked } from 'marked'

/** HTML 实体转义（拼接进 HTML 属性/文本前的唯一正确方式） */
export function escapeHtml(s: string): string {
  return (s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const renderer = markRaw(new marked.Renderer())
renderer.link = function ({ href, text }) {
  // 属性值必须转义：URL/链接文本里的引号可逃逸属性上下文
  return `<a href="${escapeHtml(href || '')}" target="_blank" rel="noopener">${escapeHtml(text || '')}</a>`
}
marked.setOptions({ renderer, breaks: true, gfm: true })

/** Markdown → 消毒后的 HTML（渲染失败时返回转义后的原文，绝不让未消毒文本进 v-html） */
export function renderMarkdown(content: string): string {
  try {
    const html = marked.parse(content) as string
    // target="_blank" 默认会被剥离，显式保留
    return DOMPurify.sanitize(html, { ADD_ATTR: ['target'] })
  } catch {
    return DOMPurify.sanitize(escapeHtml(content))
  }
}
