<template>
  <div class="case-list-view">
    <div class="cl-header">
      <div>
        <h2 class="page-title">案件管理</h2>
        <p class="page-subtitle">管理您的全部案件</p>
      </div>
      <div class="cl-header-actions">
        <el-popconfirm title="演示案件会清除当前所有数据，确认继续？" @confirm="createDemoCase">
          <template #reference>
            <el-button :loading="seeding">
              <el-icon><MagicStick /></el-icon> 演示案件
            </el-button>
          </template>
        </el-popconfirm>
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon> 新建案件
        </el-button>
      </div>
    </div>
    <!-- Stats row -->
    <div class="cl-stats">
      <div class="cl-stat" :class="{ active: !filterStage }" @click="filterStage = null">
        <span class="cl-stat-num">{{ matterStore.matters.length }}</span>
        <span class="cl-stat-label">全部</span>
      </div>
      <div v-for="s in stages" :key="s" class="cl-stat"
        :class="{ active: filterStage === s }" @click="filterStage = filterStage === s ? null : s">
        <span class="cl-stat-num">{{ matterStore.mattersByStage[s].length }}</span>
        <span class="cl-stat-label">{{ s }}</span>
      </div>
    </div>
    <!-- Search & filter -->
    <div class="cl-search-row">
      <el-input v-model="searchText" placeholder="搜索案件名称、当事人、案号、案由..." clearable
        :prefix-icon="Search" size="small" style="max-width:360px" />
      <el-select v-model="filterProcedureStage" placeholder="审级" clearable size="small" style="width:120px">
        <el-option v-for="s in PROCEDURE_STAGES" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filterRiskLevel" placeholder="风险" clearable size="small" style="width:100px">
        <el-option v-for="r in RISK_LEVELS" :key="r.value" :label="r.label" :value="r.value" />
      </el-select>
    </div>
    <!-- Sort -->
    <div class="cl-sort-row">
      <el-radio-group v-model="sortBy" size="small" class="cl-sort">
        <el-radio-button value="created">创建时间</el-radio-button>
        <el-radio-button value="updated">更新时间</el-radio-button>
        <el-radio-button value="deadline">截止日期</el-radio-button>
        <el-radio-button value="claimAmount">标的额</el-radio-button>
      </el-radio-group>
    </div>
    <!-- Case list -->
    <div v-if="filteredCases.length === 0" class="empty-state">
      <el-icon size="36" color="var(--legal-text-muted)"><FolderOpened /></el-icon>
      <p>暂无案件</p>
      <el-button size="small" type="primary" style="margin-top:10px" @click="showCreateDialog = true">
        创建第一个案件
      </el-button>
    </div>
    <div v-else class="cl-list">
      <div v-for="m in filteredCases" :key="m.id" class="cl-row" @click="selectCase(m.id)">
        <div class="cl-row-left">
          <div class="cl-row-title">
            {{ m.title }}
            <el-tag v-if="m.riskLevel" size="small" :color="riskLevelColor(m.riskLevel)" effect="dark" class="cl-risk-tag">
              {{ RISK_LEVEL_LABELS[m.riskLevel] }}
            </el-tag>
          </div>
          <div class="cl-row-meta">
            <span class="cl-row-client">{{ m.client }}</span>
            <span v-if="m.clientRole" class="cl-row-sep">&middot;</span>
            <span v-if="m.clientRole" class="cl-row-role">{{ CLIENT_ROLE_LABELS[m.clientRole] }}</span>
            <span class="cl-row-sep">&middot;</span>
            <span>{{ m.practiceArea }}</span>
            <span v-if="m.caseCause" class="cl-row-sep">&middot;</span>
            <span v-if="m.caseCause" class="cl-row-cause">{{ m.caseCause }}</span>
            <span v-if="m.caseNumber" class="cl-row-sep">&middot;</span>
            <span v-if="m.caseNumber" class="cl-row-case-num">{{ m.caseNumber }}</span>
          </div>
          <div class="cl-row-badges">
            <el-tag v-if="m.procedureStage" size="small" effect="plain" type="info">
              {{ PROCEDURE_STAGE_LABELS[m.procedureStage] }}
            </el-tag>
            <span v-if="m.claimAmount !== undefined" class="cl-claim-amount">
              标的 {{ formatCurrency(m.claimAmount) }}
            </span>
            <!-- 显示最近期限（多期限模式） -->
            <span v-if="nearestDeadline(m)" class="cl-deadline" :class="deadlineUrgencyClass(nearestDeadline(m)!.date)">
              <el-icon size="12"><WarningFilled v-if="deadlineUrgencyClass(nearestDeadline(m)!.date) === 'urgent'" /></el-icon>
              {{ DEADLINE_TYPE_LABELS[nearestDeadline(m)!.type] || nearestDeadline(m)!.customLabel }}:
              {{ formatDeadline(nearestDeadline(m)!.date) }}
            </span>
          </div>
        </div>
        <div class="cl-row-right">
          <el-tag :type="stageTagType(m.stage)" size="small">{{ m.stage }}</el-tag>
        </div>
      </div>
    </div>
    <!-- Create dialog -->
    <CaseCreateDialog v-model="showCreateDialog" @created="onCaseCreated" />
  </div>
</template>
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Plus, FolderOpened, MagicStick, WarningFilled, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useMatterStore } from '../../stores/matter'
import { useCaseViewStore } from '../../stores/caseView'
import type { MatterStage, ProcedureStage, RiskLevel } from '../../types/legal'
import {
  stageTagType,
  PROCEDURE_STAGES, PROCEDURE_STAGE_LABELS,
  RISK_LEVELS, RISK_LEVEL_LABELS, CLIENT_ROLE_LABELS,
  riskLevelColor, formatCurrency,
  DEADLINE_TYPE_LABELS, getNearestDeadline, formatDeadline, deadlineUrgency,
} from '../../lib/caseConstants'
import type { Matter, DeadlineItem } from '../../types/legal'
import CaseCreateDialog from './CaseCreateDialog.vue'
const caseViewStore = useCaseViewStore()
const emit = defineEmits<{
  'select-case': [id: string]
  'new-chat': []
}>()
const matterStore = useMatterStore()
const showCreateDialog = ref(false)

watch(() => caseViewStore.showNewCaseDialogFlag, (val) => {
  if (val > 0) showCreateDialog.value = true
})
const seeding = ref(false)
const searchText = ref('')
const filterStage = ref<string | null>(null)
const filterProcedureStage = ref<ProcedureStage | null>(null)
const filterRiskLevel = ref<RiskLevel | null>(null)
const sortBy = ref<'created' | 'updated' | 'deadline' | 'claimAmount'>('created')
const stages: MatterStage[] = ['待处理', '审查中', '证据收集', '诉讼中', '执行中', '调解中', '已完成', '已归档']
const filteredCases = computed(() => {
  let result = matterStore.matters
  if (filterStage.value) result = result.filter(m => m.stage === filterStage.value)
  if (filterProcedureStage.value) result = result.filter(m => m.procedureStage === filterProcedureStage.value)
  if (filterRiskLevel.value) result = result.filter(m => m.riskLevel === filterRiskLevel.value)
  if (searchText.value.trim()) {
    const q = searchText.value.trim().toLowerCase()
    result = result.filter(m =>
      m.title.toLowerCase().includes(q) ||
      m.client.toLowerCase().includes(q) ||
      (m.counterparty && m.counterparty.toLowerCase().includes(q)) ||
      (m.caseNumber && m.caseNumber.toLowerCase().includes(q)) ||
      (m.caseCause && m.caseCause.toLowerCase().includes(q))
    )
  }
  // Sort
  const sorted = [...result]
  if (sortBy.value === 'created') {
    sorted.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
  } else if (sortBy.value === 'updated') {
    sorted.sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime())
  } else if (sortBy.value === 'deadline') {
    // 多期限模型：按最近的现行期限排（legacy deadline 字段仅兜底）
    const dlOf = (m: Matter) => getNearestDeadline(m.deadlines)?.date || m.deadline || ''
    sorted.sort((a, b) => {
      const da = dlOf(a)
      const db = dlOf(b)
      if (!da && !db) return 0
      if (!da) return 1
      if (!db) return -1
      return new Date(da).getTime() - new Date(db).getTime()
    })
  } else if (sortBy.value === 'claimAmount') {
    sorted.sort((a, b) => (b.claimAmount || 0) - (a.claimAmount || 0))
  }
  return sorted
})
async function createDemoCase() {
  seeding.value = true
  await matterStore.seedDemoCase()
  ElMessage.success('演示案件已创建')
  seeding.value = false
  // Navigate to the created case (it's at index 0)
  const freshCases = matterStore.matters
  if (freshCases.length > 0) {
    emit('select-case', freshCases[0].id)
  }
}

function selectCase(id: string) {
  emit('select-case', id)
}
function onCaseCreated(matterId: string) {
  showCreateDialog.value = false
  // 成功提示由 CaseCreateDialog 发出（含案件名称），此处不再重复 toast
  emit('select-case', matterId)
}

/** 获取案件最近期限（用于列表展示） */
function nearestDeadline(m: Matter): DeadlineItem | null {
  return getNearestDeadline(m.deadlines)
}

/** 期限紧急程度 CSS 类（保持与旧版兼容的样式名） */
function deadlineUrgencyClass(dateStr: string): 'normal' | 'soon' | 'urgent' {
  const u = deadlineUrgency(dateStr)
  if (u === 'overdue' || u === 'critical') return 'urgent'
  if (u === 'warning' || u === 'soon') return 'soon'
  return 'normal'
}
</script>
<style scoped>
.case-list-view {
  padding: 24px 28px 40px;
  overflow: visible;   /* 外层 view-slot--page-scroll 统一提供唯一滚动条 */
  height: auto;
  min-height: 100%;
}
.cl-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.cl-header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.page-title {
  margin: 0;
  font-size: 22px;
  color: var(--legal-navy);
}
.page-subtitle {
  margin: 4px 0 0;
  color: var(--legal-text-secondary);
  font-size: 13px;
}
.cl-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.cl-stat {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  font-size: 13px;
  transition: all var(--transition-fast);
}
.cl-stat:hover, .cl-stat.active {
  border-color: var(--legal-navy);
  background: var(--el-color-primary-light-9);
}
.cl-stat-num { font-weight: var(--weight-bold); color: var(--legal-navy); font-size: 15px; }
.cl-stat-label { color: var(--legal-text-secondary); }
.cl-search-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.cl-row-title {
  font-size: 14px;
  font-weight: var(--weight-medium);
  margin-bottom: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;
}
.cl-risk-tag {
  font-size: 10px;
  padding: 0 6px;
  height: 16px;
  line-height: 16px;
  flex-shrink: 0;
}

.cl-row-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.cl-claim-amount {
  font-size: 11px;
  color: var(--legal-gold-dark);
  font-weight: 600;
  font-family: var(--font-heading);
}

.cl-row-role {
  color: var(--legal-navy);
  font-weight: 500;
}

.cl-row-cause {
  color: var(--legal-text-secondary);
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: var(--legal-text-muted);
}
.empty-state p { margin: 12px 0 0; font-size: 14px; }
.cl-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cl-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: box-shadow var(--transition-fast);
}
.cl-row:hover {
  box-shadow: var(--shadow-sm);
}
.cl-row-left {
  flex: 1;
  min-width: 0;
}
.cl-row-meta {
  font-size: 12px;
  color: var(--legal-text-muted);
}
.cl-row-sep {
  margin: 0 4px;
}
.cl-row-right {
  flex-shrink: 0;
  margin-left: 12px;
}

/* ── Sort row ── */
.cl-sort-row { margin-bottom: 12px; }
.cl-sort .el-radio-button__inner { font-size: 12px; padding: 4px 10px; }

/* ── Deadline urgency ── */
.cl-deadline {
  font-size: 11px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}
.cl-deadline.normal { color: var(--legal-text-muted); background: var(--el-fill-color-lighter); }
.cl-deadline.soon { color: var(--legal-warning); background: var(--legal-warning-bg); font-weight: 500; }
.cl-deadline.urgent { color: var(--legal-danger); background: var(--legal-danger-bg); font-weight: 600; }
</style>
