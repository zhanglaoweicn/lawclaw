<template>
  <div class="calendar-page">
    <div class="cp-header">
      <div>
        <h2 class="page-title">日程</h2>
        <p class="page-subtitle">管理开庭、会见、截止期限与个人日程</p>
      </div>
      <div class="cp-header-actions">
        <el-button @click="exportIcs">
          <el-icon><Download /></el-icon> 导出日历 (.ics)
        </el-button>
        <el-button type="primary" @click="showAdd = true">
          <el-icon><Plus /></el-icon> 新建日程
        </el-button>
      </div>
    </div>

    <!-- Filter row: type tabs + action buttons -->
    <div class="cp-filter-row">
      <div class="cp-tabs">
        <div :class="['cp-tab', { active: filterType === '' }]" @click="filterType = ''">全部</div>
        <div v-for="t in types" :key="t.key" :class="['cp-tab', { active: filterType === t.key }]" @click="filterType = t.key">
          <span class="cp-tab-dot" :style="{ background: t.color }"></span>
          {{ t.label }}
        </div>
      </div>
      <div class="cp-filter-actions">
        <el-button :class="['cp-link-btn', { active: showCompleted }]" size="small" text @click="showCompleted = !showCompleted">
          <el-icon><Select /></el-icon> 已完成
        </el-button>
        <el-dropdown @command="applyTemplate" trigger="click">
          <el-button size="small" text class="cp-link-btn">
            <el-icon><CopyDocument /></el-icon> 模板
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="t in schedule.scheduleTemplates" :key="t.id" :command="t.id">
                <span>{{ t.icon }}</span>
                <span style="margin-left:6px;font-weight:500">{{ t.name }}</span>
                <span style="margin-left:8px;font-size:11px;color:var(--legal-text-muted)">{{ t.description }}</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- Today -->
    <h3 class="cp-date-heading">今日</h3>
    <div v-if="todayItems.length === 0" class="cp-empty">
      <el-icon size="24" color="var(--legal-text-muted)"><Calendar /></el-icon>
      <p>今日无日程</p>
      <el-button size="small" type="primary" style="margin-top:8px" @click="showAdd = true">新建日程</el-button>
    </div>
    <div v-else class="cp-list">
      <div v-for="ev in todayItems" :key="ev.id" class="cp-event" :class="[`cp-${ev.type}`, { 'is-done': ev.completed }]">
        <el-checkbox :model-value="ev.completed" size="small" @change="schedule.toggleComplete(ev.id)" />
        <div class="cp-event-dot" :style="{ background: typeColor(ev.type) }"></div>
        <div class="cp-event-body" @click="openEdit(ev)">
          <div class="cp-event-title">{{ ev.title }}</div>
          <div class="cp-event-meta">
            <span class="cp-event-time">{{ formatTime(ev.dateTime) }}{{ ev.endDateTime ? ' - ' + formatTime(ev.endDateTime) : '' }}</span>
            <span v-if="ev.matterId && matterMap[ev.matterId]" class="cp-event-matter">· {{ matterMap[ev.matterId] }}</span>
            <el-tag v-if="ev.type !== 'court'" size="small" effect="plain" class="cp-event-tag">{{ typeLabel(ev.type) }}</el-tag>
            <span v-else class="cp-event-tag cp-court-tag">开庭</span>
          </div>
          <div v-if="ev.note" class="cp-event-note">{{ ev.note }}</div>
        </div>
        <el-button text size="small" class="cp-event-del" @click.stop="removeItem(ev.id)">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- This week -->
    <h3 class="cp-date-heading">本周</h3>
    <div v-if="weekItems.length === 0" class="cp-empty"><p>本周无日程</p></div>
    <div v-else class="cp-list">
      <div v-for="ev in weekItems" :key="ev.id" class="cp-event" :class="[`cp-${ev.type}`, { 'is-done': ev.completed }]">
        <el-checkbox :model-value="ev.completed" size="small" @change="schedule.toggleComplete(ev.id)" />
        <div class="cp-event-dot" :style="{ background: typeColor(ev.type) }"></div>
        <div class="cp-event-body" @click="openEdit(ev)">
          <div class="cp-event-title">{{ ev.title }}</div>
          <div class="cp-event-meta">
            <span class="cp-event-time">{{ formatDateTime(ev.dateTime) }}{{ ev.endDateTime ? ' - ' + formatTime(ev.endDateTime) : '' }}</span>
            <span v-if="ev.matterId && matterMap[ev.matterId]" class="cp-event-matter">· {{ matterMap[ev.matterId] }}</span>
            <el-tag v-if="ev.type !== 'court'" size="small" effect="plain" class="cp-event-tag">{{ typeLabel(ev.type) }}</el-tag>
            <span v-else class="cp-event-tag cp-court-tag">开庭</span>
          </div>
        </div>
        <el-button text size="small" class="cp-event-del" @click.stop="removeItem(ev.id)">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- Later (grouped by date) -->
    <h3 class="cp-date-heading">更远日期</h3>
    <div v-if="laterItems.length === 0" class="cp-empty"><p>暂无其他日程</p></div>
    <div v-else>
      <div v-for="group in groupedLaterItems" :key="group.date" class="cp-date-group">
        <div class="cp-date-group-title">{{ group.dateLabel }}</div>
        <div class="cp-list">
          <div v-for="ev in group.items" :key="ev.id" class="cp-event" :class="[`cp-${ev.type}`, { 'is-done': ev.completed }]">
            <el-checkbox :model-value="ev.completed" size="small" @change="schedule.toggleComplete(ev.id)" />
            <div class="cp-event-dot" :style="{ background: typeColor(ev.type) }"></div>
            <div class="cp-event-body" @click="openEdit(ev)">
              <div class="cp-event-title">{{ ev.title }}</div>
              <div class="cp-event-meta">
                <span class="cp-event-time">{{ formatTime(ev.dateTime) }}{{ ev.endDateTime ? ' - ' + formatTime(ev.endDateTime) : '' }}</span>
                <span v-if="ev.matterId && matterMap[ev.matterId]" class="cp-event-matter">· {{ matterMap[ev.matterId] }}</span>
              </div>
              <div v-if="ev.note" class="cp-event-note">{{ ev.note }}</div>
            </div>
            <el-button text size="small" class="cp-event-del" @click.stop="removeItem(ev.id)">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Completed items (only when toggled) -->
    <template v-if="showCompleted && completedItems.length > 0">
      <h3 class="cp-date-heading cp-date-heading-done">
        <el-icon size="14"><Select /></el-icon> 已完成 ({{ completedItems.length }})
      </h3>
      <div class="cp-list">
        <div v-for="ev in completedItems.slice(0, 20)" :key="ev.id" class="cp-event is-done" :class="`cp-${ev.type}`">
          <el-checkbox :model-value="true" size="small" @change="schedule.toggleComplete(ev.id)" />
          <div class="cp-event-dot" :style="{ background: typeColor(ev.type) }"></div>
          <div class="cp-event-body">
            <div class="cp-event-title">{{ ev.title }}</div>
            <div class="cp-event-meta">
              <span class="cp-event-time">{{ formatDateTime(ev.dateTime) }}</span>
              <span v-if="ev.matterId && matterMap[ev.matterId]" class="cp-event-matter">· {{ matterMap[ev.matterId] }}</span>
            </div>
          </div>
          <el-button text size="small" class="cp-event-del" @click.stop="removeItem(ev.id)">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </template>

    <div class="cp-summary">
      共 {{ filteredItems.length }} 项 · {{ todayItems.length }} 项今日
    </div>

    <!-- Add Dialog -->
    <el-dialog v-model="showAdd" :title="editingItem ? '编辑日程' : '新建日程'" width="460px">
      <el-form label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="如：会见当事人、调取证据..." />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="开始时间" required>
              <el-date-picker v-model="form.dateTime" type="datetime" placeholder="选择日期时间" style="width:100%"
                value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间">
              <el-date-picker v-model="form.endDateTime" type="datetime" placeholder="可选" style="width:100%"
                value-format="YYYY-MM-DDTHH:mm:ss" clearable />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width:100%">
            <el-option v-for="t in types" :key="t.key" :label="t.label" :value="t.key">
              <span class="type-opt"><span class="type-dot" :style="{ background: t.color }"></span>{{ t.label }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="关联案件（可选）">
          <el-select v-model="form.matterId" placeholder="不关联案件" style="width:100%" clearable filterable>
            <el-option v-for="m in matterStore.matters" :key="m.id" :label="m.title" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="可选备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" :disabled="!form.title || !form.dateTime" @click="onSave">
          {{ editingItem ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Plus, Calendar, Close, Select, CopyDocument, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMatterStore } from '../stores/matter'
import { useScheduleStore } from '../stores/schedule'
import { buildIcs, downloadIcs } from '../lib/ics'
import type { ScheduleItem, ScheduleType } from '../types/legal'

const matterStore = useMatterStore()
const schedule = useScheduleStore()

/** 把全部日程导出为 .ics，可导入手机日历 / Outlook */
function exportIcs() {
  const source = schedule.items
  if (!source.length) {
    ElMessage.warning('暂无日程可导出')
    return
  }
  const ics = buildIcs(source.map(i => ({
    title: i.title,
    dateTime: i.dateTime,
    endDateTime: i.endDateTime,
    type: i.type,
    note: i.note,
    completed: i.completed,
  })))
  const d = new Date()
  const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
  downloadIcs(ics, `lawclaw-日程-${stamp}.ics`)
  ElMessage.success(`已导出 ${source.length} 项日程，可导入手机日历`)
}

const filterType = ref('')
const showCompleted = ref(false)
const showAdd = ref(false)
const editingItem = ref<ScheduleItem | null>(null)

const types = [
  { key: 'court' as const, label: '开庭', color: '#b22222' },
  { key: 'meeting' as const, label: '会议/会见', color: '#7c3aed' },
  { key: 'deadline' as const, label: '截止期限', color: '#b8973e' },
  { key: 'appointment' as const, label: '约见/调证', color: '#2563eb' },
  { key: 'personal' as const, label: '个人', color: '#6b7280' },
]

const typeColor = (t: string) => types.find(x => x.key === t)?.color || '#6b7280'
const typeLabel = (t: string) => types.find(x => x.key === t)?.label || t

const matterMap = computed(() => {
  const map: Record<string, string> = {}
  for (const m of matterStore.matters) map[m.id] = m.title
  return map
})

const form = ref({
  title: '',
  dateTime: '',
  endDateTime: '' as string | undefined,
  type: 'meeting' as ScheduleType,
  matterId: '' as string | undefined,
  note: '',
})

// Initialize form type from store's last used type
form.value.type = schedule.lastUsedType

// Reactive filter
const filteredItems = computed(() => {
  let list = schedule.sortedItems
  if (filterType.value) list = list.filter(i => i.type === filterType.value)
  return list
})

function isToday(d: Date) {
  const n = new Date()
  return d.getDate() === n.getDate() && d.getMonth() === n.getMonth() && d.getFullYear() === n.getFullYear()
}
function isThisWeek(d: Date) {
  const n = new Date()
  const day = n.getDay()
  const diff = day === 0 ? 6 : day - 1  // Monday = 0, Sunday = 6
  const ws = new Date(n)
  ws.setDate(n.getDate() - diff)
  ws.setHours(0, 0, 0, 0)
  const we = new Date(ws)
  we.setDate(ws.getDate() + 7)
  return d >= ws && d < we
}

const todayItems = computed(() => {
  const all = filteredItems.value.filter(i => isToday(new Date(i.dateTime)))
  return showCompleted.value ? all : all.filter(i => !i.completed)
})
const weekItems = computed(() => {
  const all = filteredItems.value.filter(i => !isToday(new Date(i.dateTime)) && isThisWeek(new Date(i.dateTime)))
  return showCompleted.value ? all : all.filter(i => !i.completed)
})
const laterItems = computed(() => {
  const all = filteredItems.value.filter(i => !isToday(new Date(i.dateTime)) && !isThisWeek(new Date(i.dateTime)))
  return showCompleted.value ? all : all.filter(i => !i.completed)
})

const groupedLaterItems = computed(() => {
  const groups: { dateLabel: string; date: string; items: ScheduleItem[] }[] = []
  const dateMap = new Map<string, ScheduleItem[]>()
  for (const item of laterItems.value) {
    const d = new Date(item.dateTime)
    const dateKey = d.toLocaleDateString('zh-CN')
    if (!dateMap.has(dateKey)) dateMap.set(dateKey, [])
    dateMap.get(dateKey)!.push(item)
  }
  for (const [dateKey, items] of dateMap) {
    const sampleDate = new Date(items[0].dateTime)
    const label = sampleDate.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' })
    groups.push({ dateLabel: label, date: dateKey, items })
  }
  return groups.sort((a, b) => new Date(a.items[0].dateTime).getTime() - new Date(b.items[0].dateTime).getTime())
})

const completedItems = computed(() => {
  if (!showCompleted.value) return []
  return schedule.sortedItems.filter(i => i.completed)
})

function formatTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
function formatDateTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }) + ' ' + formatTime(iso)
}

function openEdit(ev: ScheduleItem) {
  editingItem.value = ev
  form.value = {
    title: ev.title,
    dateTime: ev.dateTime,
    endDateTime: ev.endDateTime,
    type: ev.type,
    matterId: ev.matterId,
    note: ev.note || '',
  }
  showAdd.value = true
}

function resetForm() {
  form.value = { title: '', dateTime: '', endDateTime: undefined, type: schedule.lastUsedType, matterId: undefined, note: '' }
  editingItem.value = null
}

function onSave() {
  if (!form.value.title || !form.value.dateTime) return

  // Check for court conflicts
  if (form.value.type === 'court') {
    const conflicts = schedule.checkCourtConflicts(
      form.value.dateTime,
      form.value.endDateTime,
      editingItem.value?.id
    )
    if (conflicts.length > 0) {
      ElMessageBox.confirm(
        `检测到与 ${conflicts.length} 个开庭日程时间冲突：\n${conflicts.map(c => `· ${c.title}`).join('\n')}\n\n仍然保存吗？`,
        '开庭时间冲突',
        { confirmButtonText: '仍然保存', cancelButtonText: '取消', type: 'warning' }
      ).then(() => doSave()).catch(() => {})
      return
    }
  }
  doSave()
}

function doSave() {
  if (!form.value.title || !form.value.dateTime) return
  const data = {
    title: form.value.title,
    dateTime: form.value.dateTime,
    endDateTime: form.value.endDateTime || undefined,
    type: form.value.type,
    matterId: form.value.matterId || undefined,
    note: form.value.note || undefined,
    completed: false,
  }
  if (editingItem.value) {
    schedule.updateItem(editingItem.value.id, data)
    ElMessage.success('日程已更新')
  } else {
    schedule.addItem(data)
    ElMessage.success('日程已创建')
  }
  showAdd.value = false
  resetForm()
}

function applyTemplate(templateId: string) {
  const template = schedule.scheduleTemplates.find((t: any) => t.id === templateId)
  if (!template) return
  const created = schedule.applyTemplate(templateId, new Date().toISOString())
  ElMessage.success(`已创建「${template.name}」共 ${created.length} 项日程`)
}

/** 单条删除带确认（开庭/期限误删代价高） */
function removeItem(id: string) {
  ElMessageBox.confirm(
    '删除后不可恢复，确认删除该日程？',
    '删除日程',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
  ).then(() => schedule.deleteItem(id)).catch(() => {})
}

// Sync matters on mount —— 深度监听：期限的添加/编辑/撤销也要同步到日程
watch(() => matterStore.matters, () => schedule.syncFromMatters(), { deep: true, immediate: true })
</script>

<style scoped>
.calendar-page {
  padding: 24px 28px 40px;
  overflow: visible;   /* 外层 view-slot--page-scroll 统一提供唯一滚动条 */
  height: auto;
  min-height: 100%;
}

.cp-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.cp-header-actions { display: flex; gap: 8px; align-items: center; }
.page-title { margin: 0; font-size: 22px; color: var(--legal-navy); }
.page-subtitle { margin: 4px 0 0; color: var(--legal-text-secondary); font-size: 13px; }

/* ── Filter tabs ── */
.cp-tabs { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
.cp-tab {
  display: flex; align-items: center; gap: 4px;
  padding: 5px 12px; border-radius: 20px;
  font-size: 13px; cursor: pointer;
  border: 1px solid var(--el-border-color-lighter);
  color: var(--legal-text-secondary);
  transition: all var(--transition-fast);
  user-select: none;
}
.cp-tab:hover { border-color: var(--legal-navy); color: var(--legal-navy); }
.cp-tab.active { background: var(--el-color-primary-light-9); border-color: var(--legal-navy); color: var(--legal-navy); font-weight: 600; }
.cp-tab-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

/* ── Filter row ── */
.cp-filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 8px;
}
.cp-filter-actions {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-shrink: 0;
}
.cp-link-btn {
  font-size: 12px !important;
  color: var(--legal-text-muted);
  padding: 4px 8px !important;
  height: 28px;
}
.cp-link-btn:hover { color: var(--legal-navy); }
.cp-link-btn.active { color: var(--legal-gold-dark); font-weight: 600; }

/* ── Date group ── */
.cp-date-group { margin-bottom: 16px; }
.cp-date-group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--legal-navy);
  padding: 6px 0 8px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.cp-date-heading-done {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--legal-text-muted);
}

/* ── Date headings ── */
.cp-date-heading {
  font-size: 15px; color: var(--legal-navy);
  margin: 0 0 10px; padding-bottom: 6px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

/* ── Empty ── */
.cp-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 20px 0; color: var(--legal-text-muted); font-size: 13px; margin-bottom: 24px; }

/* ── Event list ── */
.cp-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 24px; }

.cp-event {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  transition: box-shadow var(--transition-fast), opacity var(--transition-fast);
}
.cp-event:hover { box-shadow: var(--shadow-sm); }
.cp-event.is-done { opacity: 0.5; }
.cp-event.is-done .cp-event-title { text-decoration: line-through; }

.cp-event-dot {
  width: 8px; height: 8px; border-radius: 50%;
  flex-shrink: 0; margin-top: 6px;
}

.cp-event-body { flex: 1; min-width: 0; cursor: pointer; }
.cp-event-title { font-size: 13px; font-weight: var(--weight-medium); margin-bottom: 2px; }
.cp-event-meta { font-size: 12px; color: var(--legal-text-muted); display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.cp-event-time { white-space: nowrap; }
.cp-event-matter { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.cp-event-tag { font-size: 10px; }
/* 开庭行内标签（court 类型行已有红色左边条，用红色描边徽章与 el-tag 区分） */
.cp-court-tag {
  display: inline-block;
  padding: 0 6px;
  border: 1px solid var(--legal-danger);
  border-radius: 4px;
  color: var(--legal-danger);
  line-height: 16px;
  font-size: 10px;
}
.cp-event-note { font-size: 12px; color: var(--legal-text-secondary); margin-top: 4px; }
.cp-event-del { opacity: 0; transition: opacity var(--transition-fast); flex-shrink: 0; }
.cp-event:hover .cp-event-del { opacity: 1; }

/* ── Summary ── */
.cp-summary { margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--el-border-color-lighter); font-size: 12px; color: var(--legal-text-muted); text-align: center; }

/* ── Type option in select ── */
.type-opt { display: flex; align-items: center; gap: 6px; }
.type-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
</style>
