/**
 * 唯一 ID 生成器
 * 替代各 store 中重复的 generateId() 实现
 */
export function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}
