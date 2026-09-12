<template>
  <!-- append-to-body：挂到 body 下渲染。否则在 MatterList 侧栏内挂载时，
       overlay 会被侧栏容器裁剪成 231px 窄条且遮挡内容无法关闭 -->
  <el-dialog v-model="visible" title="新建案件" width="720px" append-to-body @open="onOpen" :close-on-click-modal="false">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="case-form">
      <!-- ── 基本信息 ── -->
      <div class="form-section-title">基本信息</div>
      <el-row :gutter="16">
        <el-col :span="24">
          <el-form-item label="案件名称" prop="title">
            <el-input v-model="form.title" placeholder="如：张某诉李某离婚纠纷" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="业务领域" prop="practiceArea">
            <el-select v-model="form.practiceArea" placeholder="选择业务领域" style="width:100%" @change="onPracticeAreaChange">
              <el-option v-for="a in PRACTICE_AREAS" :key="a" :label="a" :value="a" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="案由" prop="caseCause">
            <el-select v-model="form.caseCause" placeholder="选择案由" filterable allow-create style="width:100%">
              <el-option v-for="c in availableCaseCauses" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="案件类型" prop="caseType">
            <el-select v-model="form.caseType" placeholder="选择案件类型" style="width:100%">
              <el-option label="民事" value="civil" />
              <el-option label="刑事" value="criminal" />
              <el-option label="行政" value="administrative" />
              <el-option label="商事" value="commercial" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="审级" prop="procedureStage">
            <el-select v-model="form.procedureStage" placeholder="选择审级" style="width:100%">
              <el-option v-for="s in PROCEDURE_STAGES" :key="s.value" :label="s.label" :value="s.value">
                <span>{{ s.label }}</span>
                <span class="opt-meta">{{ s.desc }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <!-- ── 当事人 ── -->
      <div class="form-section-title">当事人</div>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="委托人" prop="client">
            <el-input v-model="form.client" placeholder="委托人姓名/单位" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="委托人角色" prop="clientRole">
            <el-select v-model="form.clientRole" placeholder="选择委托人角色" style="width:100%">
              <el-option v-for="r in availableClientRoles" :key="r.value" :label="r.label" :value="r.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="对方当事人">
            <el-input v-model="form.counterparty" placeholder="对方姓名/单位" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="对方代理律师">
            <el-input v-model="form.opposingCounsel" placeholder="对方律师姓名" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- ── 诉讼信息 ── -->
      <div class="form-section-title">诉讼信息</div>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="案号">
            <el-input v-model="form.caseNumber" placeholder="(2026)京0105民初xxxx号" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="受理法院/机构">
            <el-input v-model="form.courtName" placeholder="如：北京市朝阳区人民法院" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="受理日期">
            <el-date-picker v-model="form.filingDate" type="date" placeholder="法院立案日" style="width:100%" value-format="YYYY-MM-DD" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="开庭日期">
            <el-date-picker v-model="form.courtDate" type="date" placeholder="下次开庭日" style="width:100%" value-format="YYYY-MM-DD" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="诉讼标的额（元）">
            <el-input-number v-model="form.claimAmount" :min="0" :step="10000" placeholder="如：5200000" style="width:100%" :controls="false" />
            <div class="amount-hint">{{ formatCurrency(form.claimAmount) }}</div>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="阶段" prop="stage">
            <el-select v-model="form.stage" placeholder="选择案件阶段" style="width:100%">
              <el-option v-for="s in ALL_STAGES.filter(s => s !== '已归档')" :key="s" :label="s" :value="s" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="关键截止日期">
            <el-date-picker v-model="form.deadline" type="date" placeholder="举证/上诉/答辩截止" style="width:100%" value-format="YYYY-MM-DD" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="风险等级">
            <el-select v-model="form.riskLevel" placeholder="选择风险等级" style="width:100%">
              <el-option v-for="r in RISK_LEVELS" :key="r.value" :label="r.label" :value="r.value">
                <span class="risk-dot" :style="{ background: r.color }"></span>
                <span>{{ r.label }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="案件描述">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="案件简述、争议焦点、当事人诉求等" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- ── 收费信息 ── -->
      <div class="form-section-title">收费信息</div>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="律师费（元）">
            <el-input-number v-model="form.fee" :min="0" :step="5000" placeholder="如：50000" style="width:100%" :controls="false" />
            <div class="amount-hint">{{ formatCurrency(form.fee) }}</div>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="收费方式">
            <el-select v-model="form.feeType" placeholder="选择收费方式" style="width:100%">
              <el-option v-for="f in FEE_TYPES" :key="f.value" :label="f.label" :value="f.value">
                <span>{{ f.label }}</span>
                <span class="opt-meta">{{ f.desc }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 利益冲突实时检查 -->
      <div v-if="conflictMatches.length > 0" class="conflict-section">
        <div class="conflict-header" :class="`conflict-header-${conflictLevel}`">
          <span class="conflict-icon">{{ CONFLICT_LEVEL_META[conflictLevel].icon }}</span>
          <span class="conflict-title">{{ CONFLICT_LEVEL_META[conflictLevel].label }}（共 {{ conflictMatches.length }} 条）</span>
          <span v-if="conflictLevel === 'blocked'" class="conflict-law">《律师法》第39条 禁止代理</span>
          <span v-else-if="conflictLevel === 'warning'" class="conflict-law">需律师书面确认</span>
        </div>
        <div class="conflict-list">
          <div v-for="(m, idx) in conflictMatches" :key="idx" class="conflict-item" :class="`conflict-item-${m.level}`">
            <div class="conflict-item-title">
              <el-tag size="small" :type="m.level === 'blocked' ? 'danger' : 'warning'" effect="dark">
                {{ m.level === 'blocked' ? '禁止' : '提示' }}
              </el-tag>
              <span class="conflict-matter" @click="goToConflictMatter(m.matterId)">
                {{ m.matterTitle }}
              </span>
              <el-tag size="small" effect="plain">{{ m.matterStage }}</el-tag>
            </div>
            <p class="conflict-desc">{{ m.description }}</p>
          </div>
        </div>
      </div>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button v-if="conflictLevel === 'blocked'" type="danger" disabled>
        ⛔ 利益冲突禁止代理
      </el-button>
      <el-button v-else-if="conflictLevel === 'warning'" type="warning" @click="onSubmitWithConfirm" :loading="submitting">
        ⚠ 确认无冲突并创建
      </el-button>
      <el-button v-else type="primary" @click="onSubmit" :loading="submitting">创建案件</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, reactive, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMatterStore } from '../../stores/matter'
import { useCaseViewStore } from '../../stores/caseView'
import type { MatterFormData, ProcedureStage, ClientRole, RiskLevel, FeeType } from '../../types/legal'
import {
  ALL_STAGES, PROCEDURE_STAGES, CLIENT_ROLES, RISK_LEVELS, FEE_TYPES,
  COMMON_CASE_CAUSES, PRACTICE_AREA_TO_CASE_TYPE, formatCurrency, suggestRiskLevel,
  CONFLICT_LEVEL_META, type ConflictMatch, type ConflictLevel,
} from '../../lib/caseConstants'

const visible = defineModel<boolean>('visible', { default: false })
const emit = defineEmits<{ created: [matterId: string] }>()

const matterStore = useMatterStore()
const caseViewStore = useCaseViewStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const PRACTICE_AREAS = Object.keys(COMMON_CASE_CAUSES)

const form = reactive<MatterFormData>({
  title: '',
  client: '',
  counterparty: '',
  practiceArea: '',
  caseCause: '',
  caseType: 'civil',
  procedureStage: 'first-instance',
  clientRole: 'plaintiff',
  stage: '待处理',
  caseNumber: '',
  description: '',
  courtName: '',
  courtDate: '',
  deadline: '',
  filingDate: '',
  opposingCounsel: '',
  claimAmount: undefined,
  riskLevel: 'medium',
  fee: undefined,
  feeType: 'fixed',
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入案件名称', trigger: 'blur' }],
  client: [{ required: true, message: '请输入委托人', trigger: 'blur' }],
  practiceArea: [{ required: true, message: '请选择业务领域', trigger: 'change' }],
  caseType: [{ required: true, message: '请选择案件类型', trigger: 'change' }],
  procedureStage: [{ required: true, message: '请选择审级', trigger: 'change' }],
  stage: [{ required: true, message: '请选择案件阶段', trigger: 'change' }],
}

/** 根据业务领域返回可用案由 */
const availableCaseCauses = computed(() => {
  if (!form.practiceArea) return []
  return COMMON_CASE_CAUSES[form.practiceArea] || []
})

/** 根据 caseType 过滤委托人角色 */
const availableClientRoles = computed(() => {
  const ct = form.caseType || 'civil'
  return CLIENT_ROLES.filter(r => r.caseTypes.includes(ct))
})

/** 业务领域变更时：自动联动 caseType、清空 caseCause、建议风险等级 */
function onPracticeAreaChange() {
  // 联动 caseType
  const mapped = form.practiceArea ? PRACTICE_AREA_TO_CASE_TYPE[form.practiceArea] : undefined
  if (mapped) form.caseType = mapped
  // 清空案由（避免脏数据）
  form.caseCause = ''
  // 重置委托人角色（如果当前角色不在新 caseType 的允许列表中）
  if (form.clientRole && !availableClientRoles.value.find(r => r.value === form.clientRole)) {
    form.clientRole = availableClientRoles.value[0]?.value as ClientRole
  }
}

/** 标的额变化时自动建议风险等级（仅当用户未手动选择时） */
function autoSuggestRisk() {
  form.riskLevel = suggestRiskLevel(form.claimAmount, form.caseType)
}

// ── 利益冲突实时检查 ──
const conflictMatches = ref<ConflictMatch[]>([])
const conflictLevel = computed<ConflictLevel>(() => matterStore.getConflictLevel(conflictMatches.value))

/** 监听 client/counterparty/opposingCounsel 变化，实时检查冲突 */
watch(
  () => [form.client, form.counterparty, form.opposingCounsel],
  ([client, counterparty, opposingCounsel]) => {
    if (!client) {
      conflictMatches.value = []
      return
    }
    conflictMatches.value = matterStore.checkConflict(
      String(client || ''),
      counterparty ? String(counterparty) : undefined,
      opposingCounsel ? String(opposingCounsel) : undefined,
    )
  },
  { immediate: true },
)

/** 跳转到冲突案件详情 */
function goToConflictMatter(matterId: string) {
  caseViewStore.showCaseDetail(matterId)
  visible.value = false
}

function onOpen() {
  // 重置表单
  Object.assign(form, {
    title: '', client: '', counterparty: '', practiceArea: '', caseCause: '',
    caseType: 'civil', procedureStage: 'first-instance', clientRole: 'plaintiff',
    stage: '待处理', caseNumber: '', description: '', courtName: '', courtDate: '',
    deadline: '', filingDate: '', opposingCounsel: '',
    claimAmount: undefined, riskLevel: 'medium', fee: undefined, feeType: 'fixed',
  })
  conflictMatches.value = []
  formRef.value?.clearValidate()
}

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate((valid) => {
    if (!valid) {
      ElMessage.warning('请完善必填字段')
      return
    }
    // 二次检查冲突（防止 watch 异步未更新）
    const matches = matterStore.checkConflict(form.client, form.counterparty, form.opposingCounsel)
    if (matterStore.getConflictLevel(matches) === 'blocked') {
      ElMessage.error('存在利益冲突（blocked），禁止创建案件')
      conflictMatches.value = matches
      return
    }
    submitting.value = true
    try {
      const matter = matterStore.addMatter({ ...form })
      ElMessage.success(`案件「${matter.title}」已创建`)
      visible.value = false
      emit('created', matter.id)
    } catch (e: any) {
      ElMessage.error(e.message || '创建失败')
    } finally {
      submitting.value = false
    }
  })
}

/** warning 级别冲突需律师书面确认后才能创建 */
async function onSubmitWithConfirm() {
  if (!formRef.value) return
  try {
    await ElMessageBox.confirm(
      `检测到 ${conflictMatches.value.length} 条潜在冲突提示。\n\n律师依法应书面记录并征得相关委托人书面同意后方可代理。\n\n请确认已获得相关委托人书面同意，或经审慎评估后认定不存在利益冲突。`,
      '利益冲突确认',
      {
        confirmButtonText: '已确认，继续创建',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false,
      },
    )
    onSubmit()
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.case-form { max-height: 65vh; overflow-y: auto; padding-right: 8px; }

/* ── 利益冲突检查 UI ── */
.conflict-section {
  margin: 12px 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--el-border-color);
}

.conflict-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
}
.conflict-header-blocked {
  background: rgba(245, 108, 108, 0.1);
  color: var(--el-color-danger);
  border-bottom: 1px solid rgba(245, 108, 108, 0.3);
}
.conflict-header-warning {
  background: rgba(230, 162, 60, 0.1);
  color: var(--el-color-warning);
  border-bottom: 1px solid rgba(230, 162, 60, 0.3);
}
.conflict-icon { font-size: 16px; }
.conflict-title { flex: 1; }
.conflict-law {
  font-size: 11px;
  font-weight: 400;
  opacity: 0.85;
}

.conflict-list {
  padding: 6px 0;
  background: var(--el-fill-color-lighter);
  max-height: 180px;
  overflow-y: auto;
}

.conflict-item {
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.conflict-item:last-child { border-bottom: none; }
.conflict-item-blocked { border-left: 3px solid var(--el-color-danger); }
.conflict-item-warning { border-left: 3px solid var(--el-color-warning); }

.conflict-item-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.conflict-matter {
  font-weight: 600;
  color: var(--legal-navy);
  cursor: pointer;
  font-size: 12px;
}
.conflict-matter:hover {
  text-decoration: underline;
  color: var(--legal-gold-dark);
}

.conflict-desc {
  margin: 0;
  font-size: 11px;
  color: var(--legal-text-secondary);
  line-height: 1.5;
}

.form-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--legal-navy);
  margin: 16px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  display: flex;
  align-items: center;
  gap: 6px;
}
.form-section-title::before {
  content: '';
  width: 3px;
  height: 12px;
  background: var(--legal-gold);
  border-radius: 2px;
}

.opt-meta {
  float: right;
  color: var(--legal-text-muted);
  font-size: 11px;
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.amount-hint {
  font-size: 11px;
  color: var(--legal-gold-dark);
  margin-top: 2px;
  font-weight: 600;
}

.risk-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}
</style>
