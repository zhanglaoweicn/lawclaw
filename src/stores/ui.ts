import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

const COLLAPSE_KEY = 'lawclaw_ui_sidebar_collapsed'
const WIDTH_KEY = 'lawclaw_ui_sidebar_width'

export const SIDEBAR_W = {
  WIDE: 232 as const,   // 展开宽度（原 280 → 缩窄 20%）
  NARROW: 64 as const,  // 折叠宽度（只显示图标）
}

function readBool(key: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(key)
    return v === null ? fallback : v === '1'
  } catch { return fallback }
}

function writeBool(key: string, v: boolean) {
  try { localStorage.setItem(key, v ? '1' : '0') } catch { /* ignore */ }
}

function readNum(key: string, fallback: number): number {
  try {
    const v = Number(localStorage.getItem(key))
    return Number.isFinite(v) && v > 0 ? v : fallback
  } catch { return fallback }
}

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref<boolean>(readBool(COLLAPSE_KEY, false))
  // 用户手动调整过的展开宽度（允许在 200-280 之间微调；默认 232）
  const sidebarWidth = ref<number>(readNum(WIDTH_KEY, SIDEBAR_W.WIDE))

  watch(sidebarCollapsed, (v) => writeBool(COLLAPSE_KEY, v))
  watch(sidebarWidth, (v) => { try { localStorage.setItem(WIDTH_KEY, String(v)) } catch { /* ignore */ } })

  function toggleSidebar() { sidebarCollapsed.value = !sidebarCollapsed.value }
  function setSidebarCollapsed(v: boolean) { sidebarCollapsed.value = v }
  function setSidebarWidth(px: number) {
    const clamped = Math.max(200, Math.min(280, Math.round(px)))
    sidebarWidth.value = clamped
  }
  function resetSidebarWidth() { sidebarWidth.value = SIDEBAR_W.WIDE }

  /** CSS 用：当前实际生效宽度（折叠态返回 NARROW） */
  const effectiveSidebarPx = () =>
    sidebarCollapsed.value ? SIDEBAR_W.NARROW : sidebarWidth.value

  return {
    sidebarCollapsed,
    sidebarWidth,
    toggleSidebar,
    setSidebarCollapsed,
    setSidebarWidth,
    resetSidebarWidth,
    effectiveSidebarPx,
  }
})
