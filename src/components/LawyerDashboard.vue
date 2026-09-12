<template>
  <div class="dashboard">
    <!-- Header Area -->
    <div class="dashboard-header">
      <div>
        <h2 class="page-title">工作台</h2>
        <p class="page-subtitle">{{ greeting }}，{{ setupStore.profile?.name || '律师' }}</p>
      </div>
      <div class="header-actions">
        <el-button text class="header-action-btn" @click="$emit('show-calendar')">
          <el-icon><Calendar /></el-icon> 今日日程
        </el-button>
        <el-button text class="header-action-btn" @click="$emit('show-matters')">
          <el-icon><FolderOpened /></el-icon> 所有案件
        </el-button>
        <el-button type="primary" @click="$emit('show-chat')">
          <el-icon><ChatDotRound /></el-icon> 助理
        </el-button>
      </div>
    </div>

    <!-- Quick Question Bar (独立律师快捷提问) -->
    <div class="quick-question-bar">
      <el-input
        v-model="quickQuestion"
        placeholder="输入法律问题，快速获得专业分析…（如：违约金过高如何调整？）"
        size="large"
        class="qq-input"
        @keyup.enter="submitQuickQuestion"
      >
        <template #prefix>
          <el-icon color="var(--legal-navy)"><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" size="large" class="qq-btn" :disabled="!quickQuestion.trim()" @click="submitQuickQuestion">
        <el-icon><Promotion /></el-icon>
        <span>提问</span>
      </el-button>
    </div>

    <!-- Urgent Deadlines (紧急期限警告) -->
    <div v-if="urgentDeadlines.length > 0" class="deadlines-section">
      <div class="deadlines-header">
        <h3 class="section-title deadline-title">
          <el-icon size="14" color="var(--legal-danger)"><AlarmClock /></el-icon>
          紧急期限
        </h3>
        <span class="deadline-count">{{ urgentDeadlines.length }}</span>
      </div>
      <div class="deadlines-list">
        <div v-for="d in urgentDeadlines" :key="d.dlId" class="deadline-item" :class="`deadline-${d.urgency}`" @click="emit('open-matter', d.id)">
          <div class="deadline-date">
            <span class="deadline-days">{{ d.daysText }}</span>
            <span class="deadline-label">{{ d.dateText }}</span>
          </div>
          <div class="deadline-body">
            <span class="deadline-matter">{{ d.title }}</span>
            <span class="deadline-type">{{ d.deadlineType }}</span>
          </div>
          <el-tag size="small" :type="deadlineStatusLabel(d.daysRemaining).type" effect="dark">
            {{ deadlineStatusLabel(d.daysRemaining).text }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- ═══ 值守助手（定时监控 + AI 晨报） ═══ -->
    <div v-if="watchdogVisible" class="watchdog-section">
      <div class="watchdog-header">
        <h3 class="section-title">
          <el-icon size="14" color="var(--legal-navy)"><AlarmClock /></el-icon>
          值守助手
          <span class="watchdog-meta">最近扫描 {{ watchdog.syncedAt ? watchdog.syncedAt.slice(11, 16) : '—' }} · {{ watchdog.matters }} 案在册</span>
        </h3>
        <div style="display:flex;gap:6px">
          <el-button size="small" text :loading="briefingLoading" @click="runBriefing">
            <el-icon><Promotion /></el-icon> 生成 AI 晨报
          </el-button>
        </div>
      </div>
      <div v-if="watchdog.alerts.length" class="watchdog-alerts">
        <div v-for="(a, i) in watchdog.alerts.slice(0, 4)" :key="i" class="watchdog-alert" :class="'wa-' + a.kind">
          <el-tag size="small" :type="a.kind === 'overdue' ? 'danger' : a.kind === 'court' ? 'warning' : 'info'" effect="dark">
            {{ a.kind === 'overdue' ? '逾期' : a.kind === 'court' ? '开庭' : a.kind === 'due-soon' ? '临期' : '停滞' }}
          </el-tag>
          <span class="wa-matter">{{ a.matter }}</span>
          <span class="wa-detail">{{ a.detail }}（{{ a.date }}）</span>
        </div>
        <div v-if="watchdog.alerts.length > 4" style="font-size:11px;color:var(--legal-text-muted)">还有 {{ watchdog.alerts.length - 4 }} 项…</div>
      </div>
      <div v-else style="font-size:12px;color:var(--legal-success);padding:4px 0">✓ 扫描完成：无逾期期限、临期事项或停滞案件</div>
      <div v-if="briefingLoading" style="font-size:12px;color:var(--legal-text-muted);padding:6px 0">
        <el-icon class="is-loading"><Loading /></el-icon> 值守助手正在分析案件扫描结果…
      </div>
      <div v-else-if="briefing" class="watchdog-briefing" v-html="briefingHtml"></div>
    </div>

    <!-- Today's Schedule -->
    <div class="schedule-section">
      <div class="schedule-header">
        <h3 class="section-title">今日待办</h3>
        <el-button v-if="todayEvents.length > 0" text size="small" @click="$emit('show-calendar')">查看全部</el-button>
      </div>
      <div v-if="todayEvents.length === 0" class="schedule-empty">
        <el-icon size="20" color="var(--legal-text-muted)"><Calendar /></el-icon>
        <span>今日无待办事项</span>
      </div>
      <div v-else class="schedule-list">
        <div v-for="ev in todayEvents" :key="ev.id" class="schedule-item" :class="`schedule-${ev.type}`" @click="$emit('show-calendar')">
          <div class="schedule-dot"></div>
          <div class="schedule-body">
            <span class="schedule-title">{{ ev.title }}</span>
            <span class="schedule-matter">{{ ev.matterTitle }}</span>
          </div>
          <el-tag size="small" :type="tagTypeFor(ev.type)" effect="plain">
            {{ ev.typeLabel }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-grid">
      <div class="stat-bento stat-bento-accent">
        <div class="stat-icon">&#x2696;</div>
        <div class="stat-body">
          <div class="stat-value">{{ matterStore.activeMatters.length }}</div>
          <div class="stat-label">进行中案件</div>
        </div>
      </div>
      <div class="stat-bento">
        <div class="stat-icon">&#x1F4C5;</div>
        <div class="stat-body">
          <div class="stat-value">{{ monthlyNew }}</div>
          <div class="stat-label">本月新增</div>
        </div>
      </div>
      <div class="stat-bento">
        <div class="stat-icon">&#x23F3;</div>
        <div class="stat-body">
          <div class="stat-value">{{ pendingCount }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </div>
      <div class="stat-bento">
        <div class="stat-icon">&#x1F4AC;</div>
        <div class="stat-body">
          <div class="stat-value">{{ chatStore.sessions.length }}</div>
          <div class="stat-label">会话总数</div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <h3 class="section-title">快捷操作</h3>
    <div class="actions-bento">
      <div v-for="action in quickActions" :key="action.id"
        class="action-bento-card"
        :style="`--accent:${action.color}`"
        @click="triggerAction(action)">
        <div class="action-icon-circle" :style="`background:${action.color}14;color:${action.color}`">
          <span>{{ action.icon }}</span>
        </div>
        <div class="action-label">{{ action.label }}</div>
        <div class="action-desc">{{ action.description }}</div>
      </div>
    </div>

    <!-- Lawyer Tools (独立律师专属工具) -->
    <div class="lawyer-tools-section">
      <div class="lawyer-tools-header">
        <h3 class="section-title">
          <el-icon size="14"><Tools /></el-icon>
          律师工具箱
        </h3>
        <span class="tools-tag">独立律师专属</span>
      </div>
      <div class="tools-bento">
        <div class="tool-bento-card" @click="$emit('open-limitation-calc')">
          <div class="tool-icon-circle">
            <span>&#x23F3;</span>
          </div>
          <div class="tool-body">
            <div class="tool-label">诉讼时效计算器</div>
            <div class="tool-desc">自动计算时效届满日，避免过期失权</div>
          </div>
          <el-icon class="tool-arrow"><ArrowRight /></el-icon>
        </div>
        <div class="tool-bento-card" @click="$emit('show-calendar')">
          <div class="tool-icon-circle">
            <span>&#x1F4C5;</span>
          </div>
          <div class="tool-body">
            <div class="tool-label">开庭日程管理</div>
            <div class="tool-desc">开庭日期、答辩期限、上诉期限提醒</div>
          </div>
          <el-icon class="tool-arrow"><ArrowRight /></el-icon>
        </div>
        <div class="tool-bento-card" @click="$emit('show-matters')">
          <div class="tool-icon-circle">
            <span>&#x1F4CB;</span>
          </div>
          <div class="tool-body">
            <div class="tool-label">案件台账</div>
            <div class="tool-desc">按阶段管理案件，关联技能推荐</div>
          </div>
          <el-icon class="tool-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- Bottom: Matters & Sessions -->
    <div class="bottom-bento">
      <div class="bento-card bento-card-matters">
        <div class="bento-header">
          <h3>最近案件</h3>
          <el-button text size="small" @click="$emit('show-matters')">查看全部</el-button>
        </div>
        <div v-if="matterStore.activeMatters.length === 0" class="empty-state">
          <el-icon size="28" color="var(--legal-text-muted)"><Folder /></el-icon>
          <p>还没有案件</p>
          <el-button size="small" type="primary" style="margin-top:10px" @click.stop="$emit('show-matters')">
            新建案件
          </el-button>
        </div>
        <div v-for="m in matterStore.activeMatters.slice(0, 5)" :key="m.id"
          class="list-row" @click="openMatter(m)">
          <div class="list-info">
            <div class="list-title">{{ m.title }}</div>
            <div class="list-meta">{{ m.client }} &middot; {{ m.practiceArea }}</div>
          </div>
          <el-tag :type="stageType(m.stage)" size="small">{{ m.stage }}</el-tag>
        </div>
      </div>

      <div class="bento-card bento-card-sessions">
        <div class="bento-header">
          <h3>最近会话</h3>
          <el-button text size="small" @click="$emit('show-chat')">新对话</el-button>
        </div>
        <div v-if="chatStore.recentSessions.length === 0" class="empty-state">
          <el-icon size="28" color="var(--legal-text-muted)"><ChatDotRound /></el-icon>
          <p>还没有会话记录</p>
          <el-button size="small" type="primary" style="margin-top:10px" @click.stop="$emit('show-chat')">
            开始新对话
          </el-button>
        </div>
        <div v-for="s in chatStore.recentSessions.slice(0, 5)" :key="s.id"
          class="list-row" @click="openSession(s)">
          <div class="list-info">
            <div class="list-title">{{ s.title }}</div>
            <div class="list-meta">{{ s.messageCount }}轮对话 &middot; {{ timeAgo(s.updatedAt) }}</div>
          </div>
          <el-icon color="var(--legal-text-muted)"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Folder, ChatDotRound, ArrowRight, FolderOpened, Calendar, Tools, Search, Promotion, AlarmClock } from '@element-plus/icons-vue'
import { backend } from '../lib/backend'
import { markRaw } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import { useMatterStore } from '../stores/matter'
import { useChatStore } from '../stores/chat'
import { useSetupStore } from '../stores/setup'
import { useScheduleStore } from '../stores/schedule'
import type { Matter, QuickAction, QuickActionId } from '../types/legal'
import { DEADLINE_TYPE_LABELS } from '../lib/caseConstants'

interface ScheduleEvent {
  id: string
  title: string
  type: string
  typeLabel: string
  matterTitle: string
  matterId: string
}

const emit = defineEmits<{
  'show-matters': []
  'show-chat': []
  'show-calendar': []
  'quick-action': [id: QuickActionId]
  'open-matter': [id: string]
  'open-session': [id: string]
  'open-limitation-calc': []
  'quick-question': [text: string]
}>()

const matterStore = useMatterStore()
const chatStore = useChatStore()
const setupStore = useSetupStore()
const scheduleStore = useScheduleStore()

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

// ── Quick Question ──
const quickQuestion = ref('')

// ── 值守助手 ──
const watchdog = ref<{ syncedAt: string | null; matters: number; alerts: Array<{ kind: string; matter: string; detail: string; date: string; days: number }> }>({ syncedAt: null, matters: 0, alerts: [] })
const watchdogVisible = ref(false)
const briefing = ref<string | null>(null)
const briefingLoading = ref(false)
const briefingHtml = computed(() => {
  try {
    return marked.parse(briefing.value || '') as string
  } catch { return briefing.value || '' }
})

async function syncWatchdog() {
  try {
    const slim = matterStore.matters.map(m => ({
      id: m.id, title: m.title, client: m.client, stage: m.stage,
      updatedAt: m.updatedAt instanceof Date ? m.updatedAt.toISOString() : String(m.updatedAt),
      courtDate: m.courtDate || null,
      deadlines: (m.deadlines || []).map(d => ({ type: d.type, date: d.date, completed: d.completed, note: d.note })),
    }))
    await backend.watchdogSync(slim)
    watchdog.value = await backend.watchdogStatus()
    watchdogVisible.value = true
    const b = await backend.watchdogBriefing()
    if (b.found && b.output) briefing.value = b.output
  } catch (e: any) {
    // 值守为增强功能，静默降级；冷启动 WS 就绪竞态时重试一次
    (window as any).__watchdogErr = String(e?.message || e).slice(0, 120)
    setTimeout(() => { void syncWatchdog() }, 3000)
  }
}

async function runBriefing() {
  if (!watchdog.value.alerts.length) {
    ElMessage.info('当前无告警事项，暂无需生成晨报')
    return
  }
  briefingLoading.value = true
  try {
    const alertText = watchdog.value.alerts
      .map(a => `- [${a.kind === 'overdue' ? '已逾期' : a.kind === 'court' ? '开庭' : a.kind === 'due-soon' ? '临期' : '停滞'}] ${a.matter}：${a.detail}（${a.date}）`)
      .join('\n')
    const instruction = `你是 LawClaw 值守律师助手。以下是今日案件扫描结果：\n${alertText}\n\n请生成今日执业晨报：\n1) 「今日必须处理」：逐项给出具体行动建议（时限计算、法条依据）；\n2) 「本周关注」：临期与开庭事项的准备要点；\n3) 「风险提示」：停滞案件与潜在失权风险。\n简洁专业，总长不超过 400 字。`
    const setupStore = useSetupStore()
    const r = await backend.call<{ response: string }>('chat', {
      message: instruction,
      api_key: setupStore.apiKey || '',
      base_url: setupStore.baseUrl || '',
      model: setupStore.model || '',
      thread_id: 'watchdog-briefing',
    })
    briefing.value = r.response || ''
  } catch (e: any) {
    ElMessage.error((e?.message || '晨报生成失败').slice(0, 60))
  } finally {
    briefingLoading.value = false
  }
}

onMounted(() => { void syncWatchdog() })
function submitQuickQuestion() {
  const text = quickQuestion.value.trim()
  if (!text) return
  quickQuestion.value = ''
  emit('quick-question', text)
}

// ── Urgent Deadlines (从 deadlines[] 聚合，覆盖所有法定期限类型) ──
const urgentDeadlines = computed(() => {
  const now = new Date()
  const DAY = 86400000
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const items: Array<{
    id: string; dlId: string; title: string; daysText: string; dateText: string
    deadlineType: string; urgency: 'overdue' | 'critical' | 'warning'; daysRemaining: number
  }> = []
  for (const m of matterStore.activeMatters) {
    // 遍历 deadlines[] 数组（替代旧 deadline + courtDate 双字段检查）
    if (m.deadlines && m.deadlines.length > 0) {
      for (const dl of m.deadlines) {
        if (dl.completed || dl.supersededAt) continue  // 跳过已完成与已撤销（双时间线旧版本）
        const d = new Date(dl.date)
        // 按自然日差计算（Math.ceil 会把"今天晚些时候"算成 1 天）
        const dayStart = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
        const days = Math.round((dayStart - todayStart) / DAY)
        // 仅显示 30 日内到期或逾期 30 日内的期限
        if (days <= 30 && days >= -30) {
          items.push({
            id: m.id,
            dlId: dl.id,
            title: m.title,
            daysText: days < 0 ? `逾期${Math.abs(days)}天` : days === 0 ? '今天' : `${days}天`,
            dateText: `${d.getMonth() + 1}月${d.getDate()}日`,
            deadlineType: DEADLINE_TYPE_LABELS[dl.type] || (dl.customLabel || '其他期限'),
            // 三级状态：已逾期（红）/ 紧急≤7天（橙红）/ 临近（黄）
            urgency: days < 0 ? 'overdue' : days <= 7 ? 'critical' : 'warning',
            daysRemaining: days,
          })
        }
      }
    }
  }
  return items.sort((a, b) => a.daysRemaining - b.daysRemaining)
})

/** 紧急期限右侧状态标签（区分已逾期/今天/紧急/临近，避免清一色"紧急"） */
function deadlineStatusLabel(days: number): { text: string; type: 'danger' | 'warning' | 'info' } {
  if (days < 0) return { text: `已逾期`, type: 'danger' }
  if (days === 0) return { text: '今天到期', type: 'danger' }
  if (days <= 7) return { text: '紧急', type: 'warning' }
  return { text: '临近', type: 'info' }
}

const monthlyNew = computed(() => {
  const d = new Date(); d.setDate(1); d.setHours(0,0,0,0)
  return matterStore.matters.filter(m => m.createdAt >= d).length
})

const pendingCount = computed(() => matterStore.mattersByStage['待处理'].length || 0)

// ── Today's events ──
function isToday(d: Date) {
  const now = new Date()
  return d.getDate() === now.getDate() && d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
}

const todayEvents = computed<ScheduleEvent[]>(() => {
  return scheduleStore.sortedItems
    .filter(i => !i.completed && isToday(new Date(i.dateTime)))
    .slice(0, 8)
    .map(i => {
      const matterTitle = i.matterId
        ? matterStore.matters.find(m => m.id === i.matterId)?.title || ''
        : ''
      const typeLabelMap: Record<string, string> = {
        court: '开庭', meeting: '会议', deadline: '截止', appointment: '外勤', personal: '个人',
      }
      return {
        id: i.id,
        title: i.title,
        type: i.type,
        typeLabel: typeLabelMap[i.type] || i.type,
        matterTitle,
        matterId: i.matterId || '',
      }
    })
})

function tagTypeFor(type: string) {
  const map: Record<string, string> = {
    court: 'danger', meeting: 'primary', deadline: 'warning',
    appointment: 'info', personal: 'info',
  }
  return map[type] || 'info'
}

const quickActions: QuickAction[] = [
  { id: 'legal-research', label: '法规检索', icon: '📖', description: '查询法律法规、司法解释', color: '#2a3f6a', prompt: '检索民法典关于违约金的规定' },
  { id: 'contract-review', label: '合同审查', icon: '📋', description: '审查合同条款，识别风险', color: '#2d7d4e', prompt: '帮我审查一份合同的重点条款' },
  { id: 'document-draft', label: '文书起草', icon: '✍️', description: '起诉状、答辩状、合同文书', color: '#b8973e', prompt: '起草一份民事起诉状的提纲' },
  { id: 'fee-calc', label: '诉讼费计算', icon: '🧮', description: '诉讼费、保全费、执行费', color: '#b22222', prompt: '帮我计算诉讼费' },
]

function stageType(stage: string) {
  const map: Record<string, string> = { '待处理': 'info', '审查中': 'warning', '证据收集': 'warning', '诉讼中': 'danger', '执行中': 'warning', '调解中': 'warning', '已完成': 'success', '已归档': 'info' }
  return map[stage] || 'info'
}

function timeAgo(date: Date) {
  const diff = Date.now() - new Date(date).getTime()
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${Math.floor(diff / 86400000)}天前`
}

function triggerAction(action: QuickAction) {
  emit('quick-action', action.id)
}

function openMatter(m: Matter) {
  emit('open-matter', m.id)
}

function openSession(s: { id: string }) {
  emit('open-session', s.id)
}
</script>

<style scoped>
.dashboard {
  padding: 24px 28px 40px;
  max-width: 1200px;
  margin: 0 auto;
  overflow: visible;   /* 外层 view-slot--page-scroll 统一提供唯一滚动条 */
  height: auto;
  min-height: 100%;
}

@media (min-width: 1600px) {
  .dashboard { max-width: 90%; }
}

/* ── Header ── */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}

.page-title { margin: 0; font-size: 22px; color: var(--legal-navy); }
.page-subtitle { margin: 4px 0 0; color: var(--legal-text-secondary); font-size: 13px; }
.header-actions { display: flex; gap: 8px; }
.header-action-btn { font-size: 13px; color: var(--legal-text-secondary); }

/* ── Quick Question Bar ── */
.quick-question-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}
.qq-input { flex: 1; }
.qq-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  box-shadow: 0 0 0 1px var(--el-border-color);
  transition: box-shadow 0.2s;
}
.qq-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--legal-gold);
}
.qq-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--legal-gold);
}
.qq-input :deep(.el-input__inner) {
  font-size: 14px;
  height: 44px;
}
.qq-btn {
  border-radius: var(--radius-lg);
  height: 44px;
  padding: 0 20px;
  font-size: 14px;
  font-weight: var(--weight-semibold);
  white-space: nowrap;
}

/* ── Urgent Deadlines ── */
.deadlines-section {
  background: linear-gradient(135deg, rgba(178,34,34,0.04), rgba(230,162,60,0.04));
  border: 1px solid rgba(178,34,34,0.15);
  border-radius: var(--radius-lg);
  padding: 14px 18px;
  margin-bottom: 20px;
}
.deadlines-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.deadline-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  color: var(--legal-danger);
}
.deadline-count {
  font-size: 11px;
  font-weight: var(--weight-bold);
  padding: 1px 8px;
  background: var(--legal-danger);
  color: #fff;
  border-radius: 10px;
}
.deadlines-list { display: flex; flex-direction: column; gap: 6px; }
.deadline-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  background: var(--legal-bg-card);
  border-radius: var(--radius-sm);
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: all 0.15s;
}
.deadline-item:hover { background: var(--el-fill-color-light); }
/* 三级状态色：已逾期（深红底）/ 紧急（红条）/ 临近（黄条） */
.deadline-overdue {
  border-left-color: var(--legal-danger);
  background: color-mix(in srgb, var(--legal-danger) 8%, var(--legal-bg-card));
}
.deadline-critical { border-left-color: var(--legal-danger); }
.deadline-warning { border-left-color: var(--legal-warning); }
.deadline-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 56px;
  flex-shrink: 0;
}
.deadline-days {
  font-size: 16px;
  font-weight: var(--weight-bold);
  color: var(--legal-danger);
  font-family: var(--font-heading);
  line-height: 1.1;
}
.deadline-warning .deadline-days { color: var(--legal-warning); }
.deadline-label {
  font-size: 10px;
  color: var(--legal-text-muted);
  margin-top: 1px;
}
.deadline-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.deadline-matter {
  font-size: 13px;
  font-weight: var(--weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.deadline-type {
  font-size: 11px;
  color: var(--legal-text-muted);
  margin-top: 1px;
}

/* ── 值守助手 ── */
.watchdog-section {
  background: linear-gradient(135deg, rgba(42,63,106,0.05), rgba(184,151,62,0.05));
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-lg);
  padding: 14px 18px;
  margin-bottom: 20px;
}
.watchdog-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.watchdog-header .section-title { display: flex; align-items: center; gap: 6px; margin: 0; }
.watchdog-meta { font-size: 11px; font-weight: 400; color: var(--legal-text-muted); margin-left: 6px; }
.watchdog-alerts { display: flex; flex-direction: column; gap: 5px; }
.watchdog-alert {
  display: flex; align-items: center; gap: 8px; padding: 6px 10px;
  background: var(--legal-bg-card); border-radius: var(--radius-sm); font-size: 12.5px;
}
.wa-overdue { border-left: 3px solid var(--legal-danger); }
.wa-court { border-left: 3px solid var(--legal-warning); }
.wa-due-soon { border-left: 3px solid var(--legal-gold); }
.wa-stale { border-left: 3px solid var(--legal-text-muted); }
.wa-matter { font-weight: var(--weight-medium); flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 46%; }
.wa-detail { color: var(--legal-text-secondary); }
.watchdog-briefing {
  margin-top: 10px; padding: 12px 14px; font-size: 13px; line-height: 1.7;
  background: var(--legal-bg-card); border: 1px dashed var(--el-border-color); border-radius: var(--radius-sm);
}
.watchdog-briefing :deep(p) { margin: 0 0 6px; }
.watchdog-briefing :deep(ul), .watchdog-briefing :deep(ol) { padding-left: 18px; margin: 4px 0; }
.watchdog-briefing :deep(h1), .watchdog-briefing :deep(h2), .watchdog-briefing :deep(h3) { font-size: 13.5px; margin: 8px 0 4px; color: var(--legal-navy); }

/* ── Schedule section ── */
.schedule-section {
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  margin-bottom: 20px;
}

.schedule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.schedule-header .section-title { margin: 0; }

.schedule-empty {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: var(--legal-text-muted);
  font-size: 13px;
}

.schedule-list { display: flex; flex-direction: column; gap: 6px; }

.schedule-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.schedule-item:hover { background: var(--el-fill-color-light); }

.schedule-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.schedule-court .schedule-dot { background: var(--legal-danger); }
.schedule-deadline .schedule-dot { background: var(--legal-warning); }
.schedule-meeting .schedule-dot { background: #7c3aed; }
.schedule-appointment .schedule-dot { background: #2563eb; }
.schedule-personal .schedule-dot { background: #6b7280; }

.schedule-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.schedule-title {
  font-size: 13px;
  font-weight: var(--weight-medium);
}

.schedule-matter {
  font-size: 12px;
  color: var(--legal-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Stats bento ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-bento {
  background: var(--legal-bg-card);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid var(--el-border-color-lighter);
  transition: box-shadow var(--transition-base), transform var(--transition-fast);
}

.stat-bento:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }

.stat-bento-accent {
  border-left: 3px solid var(--legal-gold);
  background: linear-gradient(135deg, var(--legal-gold-bg) 0%, var(--legal-bg-card) 60%);
}

.stat-icon {
  font-size: 28px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--legal-navy-bg);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.stat-bento-accent .stat-icon { background: var(--legal-gold-bg); color: var(--legal-gold-dark); }

.stat-body { min-width: 0; }
.stat-value { font-size: 26px; font-weight: var(--weight-bold); color: var(--legal-navy); font-family: var(--font-heading); line-height: 1.1; }
.stat-label { font-size: 12px; color: var(--legal-text-muted); margin-top: 2px; }

/* ── Section title ── */
.section-title { font-size: 15px; margin: 0 0 12px; color: var(--legal-navy); }

/* ── Actions bento ── */
.actions-bento { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }

.action-bento-card {
  background: var(--legal-bg-card);
  border-radius: var(--radius-lg);
  padding: 20px 16px;
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  text-align: center;
  transition: box-shadow var(--transition-base), transform var(--transition-fast);
}

.action-bento-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }

.action-icon-circle {
  width: 48px; height: 48px; border-radius: var(--radius-lg);
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 12px; font-size: 22px;
}

.action-label { font-weight: var(--weight-semibold); font-size: 14px; color: var(--legal-text); margin-bottom: 4px; }
.action-desc { font-size: 12px; color: var(--legal-text-muted); line-height: 1.4; }

/* ── Bottom bento ── */
.bottom-bento { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

/* ── Lawyer Tools section ── */
.lawyer-tools-section {
  margin-bottom: 24px;
}

.lawyer-tools-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.lawyer-tools-header .section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.tools-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--legal-gold-bg);
  color: var(--legal-gold-dark);
  border-radius: var(--radius-sm);
  font-weight: var(--weight-medium);
}

.tools-bento {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.tool-bento-card {
  background: var(--legal-bg-card);
  border-radius: var(--radius-lg);
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: box-shadow var(--transition-base), transform var(--transition-fast), border-color var(--transition-fast);
}

.tool-bento-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: var(--legal-gold);
}

.tool-icon-circle {
  width: 40px; height: 40px; border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  background: var(--legal-navy-bg);
  flex-shrink: 0;
}

.tool-body { flex: 1; min-width: 0; }
.tool-label { font-size: 14px; font-weight: var(--weight-semibold); color: var(--legal-text); margin-bottom: 2px; }
.tool-desc { font-size: 12px; color: var(--legal-text-muted); line-height: 1.4; }
.tool-arrow { color: var(--legal-text-muted); flex-shrink: 0; transition: transform var(--transition-fast); }
.tool-bento-card:hover .tool-arrow { transform: translateX(2px); color: var(--legal-gold-dark); }

.bento-card {
  background: var(--legal-bg-card);
  border-radius: var(--radius-lg);
  padding: 20px;
  border: 1px solid var(--el-border-color-lighter);
}

.bento-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.bento-header h3 { margin: 0; font-size: 15px; color: var(--legal-navy); }

.empty-state { text-align: center; padding: 28px 0; color: var(--legal-text-muted); }
.empty-state p { margin: 8px 0 0; font-size: 13px; }

.list-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 0; cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.list-row:last-child { border-bottom: none; }
.list-row:hover { background: var(--el-fill-color); margin: 0 -8px; padding: 10px 8px; border-radius: var(--radius-sm); }
.list-info { min-width: 0; flex: 1; }
.list-title { font-size: 13px; font-weight: var(--weight-medium); margin-bottom: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.list-meta { font-size: 12px; color: var(--legal-text-muted); }
</style>
