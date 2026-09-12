<template>
  <teleport to="body">
    <transition name="ctx-fade">
      <div v-if="visible" class="ctx-overlay" @click.self="close" @contextmenu.prevent="close">
        <div class="ctx-menu" :style="{ left: pos.x + 'px', top: pos.y + 'px' }">
          <div
            v-for="(item, i) in items"
            :key="i"
            :class="['ctx-item', { 'ctx-divider': item.divider, 'ctx-danger': item.danger }]"
            @click="onClick(item)"
          >
            <template v-if="!item.divider">
              <el-icon v-if="item.icon" :size="14"><component :is="item.icon" /></el-icon>
              <span class="ctx-label">{{ item.label }}</span>
              <span v-if="item.shortcut" class="ctx-shortcut">{{ item.shortcut }}</span>
              <el-icon v-if="item.children" size="12" class="ctx-chevron"><ArrowRight /></el-icon>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import type { Component } from 'vue'

export interface ContextMenuItem {
  label?: string
  icon?: Component
  shortcut?: string
  danger?: boolean
  divider?: boolean
  children?: ContextMenuItem[]
  handler?: () => void
}

const props = defineProps<{
  visible: boolean
  pos: { x: number; y: number }
  items: ContextMenuItem[]
}>()

const emit = defineEmits<{ close: [] }>()

watch(() => props.visible, (v) => {
  if (v) {
    // Adjust position to keep menu in viewport
    const el = document.querySelector('.ctx-menu') as HTMLElement | null
    if (el) {
      const rect = el.getBoundingClientRect()
      if (rect.right > window.innerWidth) {
        el.style.left = (props.pos.x - rect.width) + 'px'
      }
      if (rect.bottom > window.innerHeight) {
        el.style.top = (props.pos.y - rect.height) + 'px'
      }
    }
  }
})

function onClick(item: ContextMenuItem) {
  if (item.divider) return
  if (item.handler) item.handler()
  if (!item.children) emit('close')
}

function close() {
  emit('close')
}
</script>

<style scoped>
.ctx-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
}

.ctx-menu {
  position: fixed;
  z-index: 10001;
  min-width: 160px;
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color);
  border-radius: var(--radius-sm);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  padding: 4px 0;
}

.ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  font-size: 13px;
  cursor: pointer;
  color: var(--legal-text);
  user-select: none;
  white-space: nowrap;
}

.ctx-item:hover { background: var(--el-fill-color-light); }
.ctx-item.ctx-danger { color: var(--legal-danger); }
.ctx-item.ctx-danger:hover { background: var(--legal-danger-bg); }

.ctx-label { flex: 1; }
.ctx-shortcut { font-size: 11px; color: var(--legal-text-muted); margin-left: 16px; }
.ctx-chevron { color: var(--legal-text-muted); }
.ctx-divider { height: 1px; background: var(--el-border-color-lighter); margin: 4px 0; padding: 0; cursor: default; }

.ctx-fade-enter-active,
.ctx-fade-leave-active { transition: opacity 0.12s ease; }
.ctx-fade-enter-from,
.ctx-fade-leave-to { opacity: 0; }
</style>
