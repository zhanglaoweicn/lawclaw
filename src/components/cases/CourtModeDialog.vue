<template>
  <el-dialog
    :model-value="visible"
    fullscreen
    :show-close="false"
    class="court-mode-dialog"
    append-to-body
  >
    <template #header>
      <div class="cm-header">
        <div class="cm-header-main">
          <span class="cm-badge">⚖️ 开庭模式</span>
          <span class="cm-title">{{ matter?.title }}</span>
        </div>
        <div class="cm-header-side">
          <span class="cm-countdown">{{ countdownText }}</span>
          <el-button size="small" @click="$emit('close')">退出开庭模式</el-button>
        </div>
      </div>
    </template>

    <div v-if="matter" class="cm-body">
      <!-- 开庭信息横幅 -->
      <div class="cm-court-banner">
        <div class="cm-court-item">
          <span class="cm-court-label">开庭时间</span>
          <span class="cm-court-value">{{ formatDate(matter.courtDate) }}{{ courtTimeSuffix }}</span>
        </div>
        <div class="cm-court-item">
          <span class="cm-court-label">法院</span>
          <span class="cm-court-value">{{ matter.courtName || '未知法院' }}</span>
        </div>
        <div class="cm-court-item">
          <span class="cm-court-label">案号</span>
          <span class="cm-court-value">{{ matter.caseNumber || '—' }}</span>
        </div>
        <div class="cm-court-item">
          <span class="cm-court-label">标的额</span>
          <span class="cm-court-value">{{ matter.claimAmount ? '¥' + Math.round(matter.claimAmount / 10000 * 100) / 100 + '万' : '—' }}</span>
        </div>
      </div>

      <div class="cm-columns">
        <!-- 左列：核对清单 + 期限 -->
        <div class="cm-col">
          <div class="cm-card">
            <div class="cm-card-title">
              庭前核对清单
              <span class="cm-check-progress">{{ checkedCount }}/{{ CHECKLIST.length }}</span>
            </div>
            <label v-for="item in CHECKLIST" :key="item" class="cm-check-item">
              <input
                type="checkbox"
                :checked="checklist.includes(item)"
                @change="toggleChecklist(item)"
              />
              <span :class="{ done: checklist.includes(item) }">{{ item }}</span>
            </label>
          </div>

          <div v-if="urgentDeadlines.length" class="cm-card">
            <div class="cm-card-title">期限提醒（7 日内 / 已逾期）</div>
            <div v-for="dl in urgentDeadlines" :key="dl.id" class="cm-deadline" :class="{ overdue: isOverdue(dl.date) }">
              <el-tag size="small" :type="isOverdue(dl.date) ? 'danger' : 'warning'" effect="dark">
                {{ isOverdue(dl.date) ? '已逾期' : '临期' }}
              </el-tag>
              <span class="cm-deadline-name">{{ DEADLINE_TYPE_LABELS[dl.type] || dl.customLabel || '期限' }}</span>
              <span class="cm-deadline-date">{{ formatDate(dl.date) }}</span>
            </div>
          </div>
        </div>

        <!-- 右列：文件 + 时间线 -->
        <div class="cm-col">
          <div class="cm-card">
            <div class="cm-card-title">案件材料（{{ matterFiles.length }}）</div>
            <div v-if="matterFiles.length === 0" class="cm-empty">尚未上传案件文件</div>
            <div v-for="f in matterFiles.slice(0, 8)" :key="f.id" class="cm-file">
              <span class="cm-file-name">{{ f.name }}</span>
              <el-tag v-if="(f as any).extractedText" size="small" effect="plain" type="success">AI可读</el-tag>
            </div>
          </div>

          <div class="cm-card">
            <div class="cm-card-title">案件时间线（最近 6 条）</div>
            <div v-if="recentEvents.length === 0" class="cm-empty">暂无时间线记录</div>
            <div v-for="ev in recentEvents" :key="ev.id" class="cm-event">
              <span class="cm-event-date">{{ formatDate(ev.createdAt) }}</span>
              <span class="cm-event-title">{{ ev.title }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部行动 -->
      <div class="cm-actions">
        <el-button type="primary" @click="$emit('ask', '请基于本案的材料与事实，生成一份庭审提纲：含争议焦点、举证质证要点、发问提纲与代理意见要点。')">
          <el-icon><MagicStick /></el-icon> AI 生成庭审提纲
        </el-button>
        <el-button @click="$emit('ask', '请预判对方当事人及代理律师在本案庭审中最可能提出的三项抗辩，并给出应对要点。')">
          AI 预判对方抗辩
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { useMatterStore } from '../../stores/matter'
import { useFileStore } from '../../stores/fileStore'
import { useTimelineStore } from '../../stores/timeline'
import { DEADLINE_TYPE_LABELS } from '../../lib/caseConstants'

const props = defineProps<{ matterId: string; visible: boolean }>()
const emit = defineEmits<{ close: []; ask: [text: string] }>()

const matterStore = useMatterStore()
const fileStore = useFileStore()
const timelineStore = useTimelineStore()

const matter = computed(() => matterStore.matters.find(m => m.id === props.matterId))
const matterFiles = computed(() => fileStore.files.filter(f => f.matterId === props.matterId))
const recentEvents = computed(() =>
  timelineStore.events.filter(e => e.matterId === props.matterId).slice(-6).reverse(),
)
const urgentDeadlines = computed(() =>
  (matter.value?.deadlines || [])
    .filter(d => !d.completed && d.supersededAt == null)
    .map(d => ({ ...d, ts: new Date(d.date).getTime() }))
    .filter(d => d.ts - Date.now() < 7 * 86400000)
    .sort((a, b) => a.ts - b.ts)
    .slice(0, 5),
)

// ── 庭前核对清单（按案件持久化） ──
const CHECKLIST = [
  '授权委托书（原件）',
  '律师事务所函 / 出庭函',
  '律师执业证',
  '证据原件（按证据目录排序）',
  '证据清单副本（对方份）',
  '代理词 / 庭审提纲',
  '诉讼费票据',
  '送达地址确认书',
]
const CHECKLIST_KEY = (id: string) => `lawclaw_court_checklist_${id}`
const checklist = ref<string[]>([])
watch(
  () => [props.visible, props.matterId] as const,
  ([vis]) => {
    if (!vis) return
    try {
      checklist.value = JSON.parse(localStorage.getItem(CHECKLIST_KEY(props.matterId)) || '[]')
    } catch {
      checklist.value = []
    }
    void timelineStore.loadEventsForMatter(props.matterId)
  },
  { immediate: true },
)
const checkedCount = computed(() => checklist.value.length)
function toggleChecklist(item: string) {
  const idx = checklist.value.indexOf(item)
  if (idx >= 0) checklist.value.splice(idx, 1)
  else checklist.value.push(item)
  localStorage.setItem(CHECKLIST_KEY(props.matterId), JSON.stringify(checklist.value))
}

// ── 展示辅助 ──
const courtTimeSuffix = computed(() => {
  const d = matter.value?.deadlines?.find(x => x.type === 'court-date')
  return d?.note && /:\d{2}/.test(d.note) ? ` ${d.note}` : ''
})
const countdownText = computed(() => {
  const cd = matter.value?.courtDate
  if (!cd) return ''
  const diff = new Date(cd).getTime() - Date.now()
  if (Number.isNaN(diff)) return ''
  const days = Math.ceil(diff / 86400000)
  if (days > 1) return `距开庭还有 ${days} 天`
  if (days === 1) return '明天开庭'
  if (days === 0) return '今天开庭'
  return '开庭日已过'
})
function formatDate(v: unknown): string {
  if (!v) return '—'
  const d = new Date(v as string)
  return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleDateString('zh-CN')
}
function isOverdue(date: string): boolean {
  return new Date(date).getTime() < Date.now()
}
</script>

<style scoped>
.cm-header { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.cm-header-main { display: flex; align-items: center; gap: 10px; min-width: 0; }
.cm-badge { font-weight: 600; color: var(--legal-gold-dark); white-space: nowrap; }
.cm-title { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cm-header-side { display: flex; align-items: center; gap: 12px; }
.cm-countdown { font-weight: 600; color: var(--legal-danger); white-space: nowrap; }

.cm-body { padding: 0 4px 16px; }
.cm-court-banner {
  display: flex; gap: 28px; flex-wrap: wrap;
  background: var(--legal-navy-bg);
  border: 1px solid var(--legal-border);
  border-radius: var(--radius-lg);
  padding: 14px 20px; margin-bottom: 14px;
}
.cm-court-item { display: flex; flex-direction: column; gap: 2px; }
.cm-court-label { font-size: 11px; color: var(--legal-text-muted); }
.cm-court-value { font-size: 14px; font-weight: 600; color: var(--legal-navy); }

.cm-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.cm-card {
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-lg);
  padding: 12px 16px; margin-bottom: 14px;
}
.cm-card-title {
  font-size: 13px; font-weight: 600; color: var(--legal-navy);
  margin-bottom: 8px; display: flex; align-items: center; gap: 8px;
}
.cm-check-progress { font-size: 11px; color: var(--legal-text-muted); font-weight: 500; }

.cm-check-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; cursor: pointer; font-size: 13px; }
.cm-check-item input { accent-color: var(--legal-navy); }
.cm-check-item .done { text-decoration: line-through; color: var(--legal-text-muted); }

.cm-deadline { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12.5px; }
.cm-deadline-name { flex: 1; }
.cm-deadline-date { color: var(--legal-text-muted); }
.cm-deadline.overdue .cm-deadline-date { color: var(--legal-danger); }

.cm-file { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12.5px; }
.cm-file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cm-event { display: flex; gap: 10px; padding: 4px 0; font-size: 12.5px; }
.cm-event-date { color: var(--legal-text-muted); white-space: nowrap; }
.cm-event-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cm-empty { font-size: 12px; color: var(--legal-text-muted); padding: 6px 0; }

.cm-actions { display: flex; gap: 10px; margin-top: 4px; }

@media (max-width: 900px) {
  .cm-columns { grid-template-columns: 1fr; }
}
</style>
