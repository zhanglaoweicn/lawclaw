<template>
  <div class="matter-list">
    <div class="action-bar">
      <el-button type="primary" size="small" style="width:100%" @click="showNewMatter = true">
        <el-icon><Plus /></el-icon> 新建案件
      </el-button>
    </div>

    <div class="search-bar" style="padding:0 12px 6px">
      <el-input v-model="matterSearch" placeholder="搜索案件..." size="small" clearable :prefix-icon="Search" />
    </div>

    <div class="matter-items">
      <div
        v-for="m in filteredMatters"
        :key="m.id"
        :class="['matter-item', { active: m.id === matterStore.activeMatterId }]"
        @click="openMatter(m)"
      >
        <div class="matter-left">
          <span class="matter-dot" :style="{ background: stageColor(m.stage) }"></span>
          <div class="matter-info">
            <div class="matter-title">{{ m.title }}</div>
            <div class="matter-meta">
              <el-tag :type="stageTagType(m.stage)" size="small">{{ m.stage }}</el-tag>
              <span v-if="fileCount(m.id) > 0" class="file-count">
                <el-icon size="12"><Document /></el-icon> {{ fileCount(m.id) }}
              </span>
            </div>
          </div>
        </div>
        <div class="matter-item-ops">
          <el-popconfirm title="确认删除此案件？" @confirm="deleteMatter(m.id)">
            <template #reference>
              <el-button text size="small" type="danger" @click.stop>
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </div>

    <div v-if="matterStore.archivedMatters.length > 0" class="archived-section">
      <el-divider style="margin:4px 12px">已归档</el-divider>
      <div
        v-for="m in matterStore.archivedMatters"
        :key="m.id"
        :class="['matter-item archived', { active: m.id === matterStore.activeMatterId }]"
        @click="openMatter(m)"
      >
        <span class="matter-dot" :style="{ background: stageColor(m.stage) }"></span>
        <span class="matter-title">{{ m.title }}</span>
      </div>
    </div>

    <CaseCreateDialog v-model="showNewMatter" @created="onCaseCreated" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Plus, Document, Delete, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useMatterStore } from '../stores/matter'
import { useFileStore } from '../stores/fileStore'
import type { Matter } from '../types/legal'
import { stageColor, stageTagType } from '../lib/caseConstants'
import CaseCreateDialog from './cases/CaseCreateDialog.vue'

defineProps<{
  /** 折叠态：该组件被 v-show 隐藏（父级控制），此 prop 仅作语义保留 */
  collapsed?: boolean
}>()

const emit = defineEmits<{
  'open-matter': [id: string]
}>()

const matterStore = useMatterStore()
const fileStore = useFileStore()

const showNewMatter = ref(false)
const matterSearch = ref('')

const filteredMatters = computed(() => {
  const q = matterSearch.value.toLowerCase().trim()
  if (!q) return matterStore.activeMatters
  return matterStore.activeMatters.filter(m =>
    m.title.toLowerCase().includes(q) || m.client.toLowerCase().includes(q)
  )
})

function fileCount(matterId: string) {
  return fileStore.files.filter(f => f.matterId === matterId).length
}

function openMatter(m: Matter) {
  matterStore.setActiveMatter(m.id)
  emit('open-matter', m.id)
}

function onCaseCreated(matterId: string) {
  showNewMatter.value = false
  const m = matterStore.matters.find(x => x.id === matterId)
  if (m) openMatter(m)
}

function deleteMatter(id: string) {
  matterStore.deleteMatter(id)
  ElMessage.success('案件已删除')
}
</script>

<style scoped>
.matter-list {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: visible;  /* 滚动交给父级 .sidebar-inner 统一管理，避免侧栏内多根滚动条 */
}

.action-bar { padding: 10px 12px 6px; }

.matter-items {
  flex: 0 1 auto;
  overflow: visible;   /* 原本 overflow-y:auto 是双滚的来源之一 */
  padding: 0 8px 4px;
}

.matter-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s;
  margin-bottom: 2px;
}

.matter-item:hover {
  background: var(--el-fill-color-light);
}

.matter-item.active {
  background: color-mix(in srgb, var(--el-color-primary-light-9) 70%, var(--legal-gold-bg) 30%);
  box-shadow: inset 2px 0 0 var(--legal-gold);
}

.matter-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.matter-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; box-shadow: 0 0 0 2px rgba(255,255,255,0); }

.matter-info { min-width: 0; flex: 1; }

.matter-title {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--legal-text);
}

.matter-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.file-count {
  font-size: 11px;
  color: var(--legal-text-muted);
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.archived-section { padding: 0 8px 12px; }
.archived-section .el-divider { margin: 4px 0; }
.matter-item.archived .matter-title { color: var(--legal-text-muted); font-size: 13px; }
</style>
