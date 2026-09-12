<template>
  <teleport to="body">
    <transition name="search-modal">
      <div v-if="visible" class="search-overlay" @click.self="close">
        <div class="search-modal">
          <div class="search-input-wrap">
            <el-icon class="search-icon"><Search /></el-icon>
            <input
              ref="inputRef"
              v-model="query"
              class="search-input"
              placeholder="搜索案件、文件、会话..."
              @keydown="onKeydown"
            />
            <span class="search-hint">
              <kbd>ESC</kbd> 关闭
            </span>
          </div>

          <!-- Results -->
          <div class="search-results" v-if="query.trim()">
            <div v-if="filteredMatters.length" class="search-group">
              <div class="search-group-title">案件</div>
              <div
                v-for="(item, i) in filteredMatters"
                :key="item.id"
                :class="['search-item', { active: activeIdx === i + 0 }]"
                @click="goToMatter(item.id)"
                @mouseenter="activeIdx = i + 0"
              >
                <el-icon><Files /></el-icon>
                <div class="search-item-body">
                  <span class="search-item-title" v-html="highlight(item.label)" />
                  <span class="search-item-meta">{{ item.meta }}</span>
                </div>
              </div>
            </div>

            <div v-if="filteredFiles.length" class="search-group">
              <div class="search-group-title">文件</div>
              <div
                v-for="(item, i) in filteredFiles"
                :key="item.id"
                :class="['search-item', { active: activeIdx === filteredMatters.length + i }]"
                @click="goToFile(item)"
                @mouseenter="activeIdx = filteredMatters.length + i"
              >
                <el-icon><Document /></el-icon>
                <div class="search-item-body">
                  <span class="search-item-title" v-html="highlight(item.label)" />
                  <span class="search-item-meta">{{ item.meta }}</span>
                </div>
              </div>
            </div>

            <div v-if="filteredSessions.length" class="search-group">
              <div class="search-group-title">会话</div>
              <div
                v-for="(item, i) in filteredSessions"
                :key="item.id"
                :class="['search-item', { active: activeIdx === filteredMatters.length + filteredFiles.length + i }]"
                @click="goToSession(item.id)"
                @mouseenter="activeIdx = filteredMatters.length + filteredFiles.length + i"
              >
                <el-icon><ChatDotRound /></el-icon>
                <div class="search-item-body">
                  <span class="search-item-title" v-html="highlight(item.label)" />
                  <span class="search-item-meta">{{ item.meta }}</span>
                </div>
              </div>
            </div>

            <div v-if="totalResults === 0" class="search-empty">
              <p>未找到 "{{ query }}" 相关结果</p>
            </div>
          </div>

          <div v-else class="search-hints">
            <div class="search-hint-row"><kbd>↑↓</kbd> 导航</div>
            <div class="search-hint-row"><kbd>Enter</kbd> 打开</div>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { Search, Files, Document, ChatDotRound } from '@element-plus/icons-vue'
import { useMatterStore } from '../stores/matter'
import { useFileStore } from '../stores/fileStore'
import { useChatStore } from '../stores/chat'

const emit = defineEmits<{
  close: []
  navigate: [view: string, params?: Record<string, string>]
}>()

const props = defineProps<{ visible: boolean }>()

const matterStore = useMatterStore()
const fileStore = useFileStore()
const chatStore = useChatStore()

const query = ref('')
const activeIdx = ref(0)
const inputRef = ref<HTMLInputElement>()

watch(() => props.visible, (v) => {
  if (v) {
    query.value = ''
    activeIdx.value = 0
    nextTick(() => inputRef.value?.focus())
  }
})

const q = computed(() => query.value.toLowerCase().trim())

const filteredMatters = computed(() => {
  if (!q.value) return []
  return matterStore.matters
    .filter(m => m.title.toLowerCase().includes(q.value) || m.client.toLowerCase().includes(q.value) || (m.caseNumber && m.caseNumber.toLowerCase().includes(q.value)))
    .slice(0, 5)
    .map(m => ({ id: m.id, label: m.title, meta: `${m.client} · ${m.stage}`, type: 'matter' as const }))
})

const filteredFiles = computed(() => {
  if (!q.value) return []
  return fileStore.files
    .filter(f => f.name.toLowerCase().includes(q.value))
    .slice(0, 5)
    .map(f => {
      const matterTitle = matterStore.matters.find(m => m.id === f.matterId)?.title || '未关联'
      return { id: f.id, label: f.name, meta: `${matterTitle} · ${f.category}`, matterId: f.matterId, type: 'file' as const }
    })
})

const filteredSessions = computed(() => {
  if (!q.value) return []
  return chatStore.sessions
    .filter(s => s.title.toLowerCase().includes(q.value))
    .slice(0, 5)
    .map(s => {
      const matterTitle = s.matterId ? matterStore.matters.find(m => m.id === s.matterId)?.title : null
      return { id: s.id, label: s.title, meta: `${s.messageCount}轮对话${matterTitle ? ` · ${matterTitle}` : ''}`, type: 'session' as const }
    })
})

const totalResults = computed(() => filteredMatters.value.length + filteredFiles.value.length + filteredSessions.value.length)

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function highlight(text: string) {
  if (!q.value) return escapeHtml(text)
  const idx = text.toLowerCase().indexOf(q.value)
  if (idx === -1) return escapeHtml(text)
  return escapeHtml(text.slice(0, idx)) + '<mark>' + escapeHtml(text.slice(idx, idx + q.value.length)) + '</mark>' + escapeHtml(text.slice(idx + q.value.length))
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (totalResults.value > 0) {
      activeIdx.value = Math.min(activeIdx.value + 1, totalResults.value - 1)
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (totalResults.value > 0) {
      activeIdx.value = Math.max(activeIdx.value - 1, 0)
    }
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (totalResults.value > 0) {
      executeActive()
    }
  } else if (e.key === 'Escape') {
    close()
  }
}

function executeActive() {
  const idx = activeIdx.value
  let offset = 0
  if (idx < filteredMatters.value.length) {
    goToMatter(filteredMatters.value[idx].id); return
  }
  offset += filteredMatters.value.length
  if (idx - offset < filteredFiles.value.length) {
    goToFile(filteredFiles.value[idx - offset]); return
  }
  offset += filteredFiles.value.length
  if (idx - offset < filteredSessions.value.length) {
    goToSession(filteredSessions.value[idx - offset].id)
  }
}

function goToMatter(id: string) {
  emit('navigate', 'cases', { matterId: id })
  close()
}

function goToFile(f: { matterId?: string; id: string }) {
  if (f.matterId) {
    emit('navigate', 'cases', { matterId: f.matterId, fileId: f.id })
  } else {
    emit('navigate', 'files')
  }
  close()
}

function goToSession(id: string) {
  chatStore.switchSession(id)
  emit('navigate', 'assistant')
  close()
}

function close() {
  emit('close')
}
</script>

<style scoped>
.search-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  justify-content: center;
  padding-top: 15vh;
  background: rgba(0,0,0,0.35);
  backdrop-filter: blur(2px);
}

.search-modal {
  width: 580px;
  max-height: 60vh;
  background: var(--legal-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: 0 12px 48px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.search-input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.search-icon { color: var(--legal-text-muted); font-size: 18px; flex-shrink: 0; }

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  font-family: var(--font-ui);
  color: var(--legal-text);
  background: transparent;
}

.search-input::placeholder { color: var(--legal-text-muted); }

.search-hint { font-size: 11px; color: var(--legal-text-muted); flex-shrink: 0; }
.search-hint kbd {
  display: inline-block;
  padding: 1px 5px;
  font-size: 10px;
  font-family: inherit;
  background: var(--el-fill-color);
  border: 1px solid var(--el-border-color);
  border-radius: 3px;
  margin: 0 2px;
}

.search-results {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0;
}

.search-group { padding: 0 0 4px; }
.search-group-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--legal-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 6px 16px 4px;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  cursor: pointer;
  color: var(--legal-text);
}

.search-item.active, .search-item:hover { background: var(--el-color-primary-light-9); }

.search-item-body {
  flex: 1;
  min-width: 0;
}

.search-item-title {
  font-size: 13px;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-item-title :deep(mark) {
  background: rgba(201,168,76,0.25);
  color: var(--legal-gold-dark);
  padding: 0 1px;
  border-radius: 2px;
}

.search-item-meta {
  font-size: 11px;
  color: var(--legal-text-muted);
}

.search-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--legal-text-muted);
  font-size: 13px;
}

.search-hints {
  display: flex;
  gap: 16px;
  padding: 10px 16px;
  justify-content: flex-end;
}

.search-hint-row {
  font-size: 11px;
  color: var(--legal-text-muted);
}

.search-hint-row kbd {
  display: inline-block;
  padding: 1px 5px;
  font-size: 10px;
  font-family: inherit;
  background: var(--el-fill-color);
  border: 1px solid var(--el-border-color);
  border-radius: 3px;
  margin-right: 4px;
}

.search-modal-enter-active,
.search-modal-leave-active {
  transition: opacity 0.15s ease;
}
.search-modal-enter-from,
.search-modal-leave-to {
  opacity: 0;
}
</style>
