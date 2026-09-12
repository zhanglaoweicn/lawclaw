<template>
  <el-dialog v-model="visible" title="诉讼时效计算器" width="620px" @open="onOpen">
    <div class="limitation-calc">
      <div class="lc-intro">
        <el-icon size="16" color="var(--legal-gold-dark)"><WarningFilled /></el-icon>
        <span>输入案件类型和事件日期，自动计算诉讼时效届满日。带 <span class="lc-star">*</span> 的类型需选择具体情形。</span>
      </div>

      <el-form label-position="top" class="lc-form">
        <el-form-item label="案件类型" required>
          <el-select v-model="caseType" placeholder="选择案件类型" style="width:100%" @change="onCaseTypeChange">
            <el-option v-for="t in caseTypes" :key="t.value" :label="t.label" :value="t.value">
              <span>{{ t.label }}</span>
              <span class="lc-option-meta">{{ t.period }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <!-- 二级子类型：劳动争议 / 行政诉讼 -->
        <el-form-item v-if="subTypeOptions.length > 0" :label="subTypeLabel" required>
          <el-select v-model="subType" :placeholder="`选择${subTypeLabel}`" style="width:100%" @change="calculate">
            <el-option v-for="opt in subTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value">
              <span>{{ opt.label }}</span>
              <span class="lc-option-meta">{{ opt.period }}</span>
            </el-option>
          </el-select>
          <div v-if="currentSubTypeNote" class="lc-subtype-note">
            <el-icon size="12"><InfoFilled /></el-icon>
            <span>{{ currentSubTypeNote }}</span>
          </div>
        </el-form-item>

        <el-form-item label="事件日期（权利受到损害之日 / 起算点）" required>
          <el-date-picker
            v-model="eventDate"
            type="date"
            placeholder="选择日期"
            style="width:100%"
            value-format="YYYY-MM-DD"
            @change="calculate"
          />
        </el-form-item>
      </el-form>

      <!-- 计算结果 -->
      <div v-if="result" class="lc-result" :class="result.status">
        <div class="lc-result-header">
          <span class="lc-result-status">
            <el-icon v-if="result.status === '已过期'" color="#f56c6c"><CircleCloseFilled /></el-icon>
            <el-icon v-else-if="result.status === '紧急'" color="#e6a23c"><WarningFilled /></el-icon>
            <el-icon v-else color="#67c23a"><CircleCheckFilled /></el-icon>
            {{ result.status }}
          </span>
          <span v-if="result.days_remaining !== undefined && result.status !== '不受时效限制'" class="lc-result-days">
            {{ result.days_remaining > 0 ? `剩余 ${result.days_remaining} 天` : `已过期 ${Math.abs(result.days_remaining)} 天` }}
          </span>
        </div>
        <div v-if="result.deadline" class="lc-result-deadline">
          <span class="lc-result-label">届满日期</span>
          <span class="lc-result-value">{{ result.deadline }}</span>
        </div>
        <div class="lc-result-law">
          <span class="lc-result-label">法律依据</span>
          <span class="lc-result-value">{{ result.law_basis }}</span>
        </div>
        <div class="lc-result-note">{{ result.note }}</div>
        <div v-if="result.warning" class="lc-result-warning">
          <el-icon size="12"><WarningFilled /></el-icon>
          <span>{{ result.warning }}</span>
        </div>
      </div>

      <!-- 支持的时效类型参考 -->
      <el-collapse class="lc-reference">
        <el-collapse-item title="查看全部诉讼时效规则" name="rules">
          <div class="lc-rules-tree">
            <div v-for="rule in allRules" :key="rule.value" class="lc-rule-group">
              <div class="lc-rule-group-title">
                <span class="lc-rule-name">{{ rule.label }}</span>
                <span class="lc-rule-period">{{ rule.period }}</span>
                <span class="lc-rule-law">{{ rule.law }}</span>
              </div>
              <div v-if="rule.subTypes?.length" class="lc-rule-subs">
                <div v-for="sub in rule.subTypes" :key="sub.value" class="lc-rule-sub" @click="selectSubRule(rule, sub)">
                  <span class="lc-rule-sub-name">{{ sub.label }}</span>
                  <span class="lc-rule-sub-period">{{ sub.period }}</span>
                  <span class="lc-rule-sub-law">{{ sub.law }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button v-if="result && result.deadline && result.status !== '已过期'" type="primary" @click="addToCalendar">
        <el-icon><Calendar /></el-icon> 添加到日历提醒
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { WarningFilled, CircleCloseFilled, CircleCheckFilled, Calendar, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { backend } from '../lib/backend'

const visible = defineModel<boolean>('visible', { default: false })
const emit = defineEmits<{ 'add-to-calendar': [date: string, title: string] }>()

interface SubTypeRule {
  value: string
  label: string
  period: string
  law: string
  note: string
  /** 不适用时效限制时设为 true */
  noLimitation?: boolean
}

interface LimitationRule {
  value: string
  label: string
  period: string
  law: string
  /** 单一规则的说明（无 subTypes 时使用） */
  note?: string
  /** 是否有子类型 */
  subTypes?: SubTypeRule[]
}

/**
 * 诉讼时效规则表
 *
 * 法律依据（截至 2026-08）：
 * - 民法典第188条：普通时效3年，最长保护期20年
 * - 劳动争议调解仲裁法第27条：一般1年；劳动报酬争议在职期间不受限；离职后1年
 * - 行政诉讼法第46条：一般6个月；未告知诉权1年；不动产20年；其他5年
 * - 国家赔偿法第39条：2年（被羁押期间不计入）
 * - 保险法第26条：人寿保险5年；其他保险2年
 * - 票据法第17条：票据追索权6个月；再追索权3个月
 * - 海商法第257条：海上货物运输1年
 */
const allRules: LimitationRule[] = [
  {
    value: '民事', label: '民事诉讼（一般）', period: '3年', law: '民法典第188条',
    subTypes: [
      { value: '民事-一般', label: '普通诉讼时效', period: '3年', law: '民法典第188条第1款',
        note: '自权利人知道或应当知道权利受到损害及义务人之日起计算。可因起诉、请求、承认、履行而中断（重新起算）；因不可抗力等中止。' },
      { value: '民事-最长保护期', label: '最长保护期', period: '20年', law: '民法典第188条第2款',
        note: '自权利被侵害之日起算，不适用诉讼时效中止、中断。超过20年人民法院不予保护，特殊情况可申请延长。' },
    ],
  },
  {
    value: '合同', label: '合同纠纷', period: '3年', law: '民法典第188、189条',
    note: '适用3年普通时效；分期履行的合同自最后一期履行期限届满之日起算。',
  },
  {
    value: '侵权', label: '侵权责任纠纷', period: '3年', law: '民法典第188条',
    note: '自受害人知道或应当知道权利受损害及义务人之日起算；人身损害自治疗终结或确诊之日起算。',
  },
  {
    value: '劳动', label: '劳动争议', period: '1年', law: '劳动争议调解仲裁法第27条',
    subTypes: [
      { value: '劳动-一般', label: '一般劳动争议', period: '1年', law: '劳动争议调解仲裁法第27条第1款',
        note: '自当事人知道或应当知道其权利被侵害之日起计算。适用于解除劳动合同、工资差额（非拖欠）、工伤待遇、年休假等争议。' },
      { value: '劳动-报酬在职', label: '拖欠劳动报酬（在职期间）', period: '不受时效限制', law: '劳动争议调解仲裁法第27条第4款',
        note: '劳动关系存续期间因拖欠劳动报酬发生争议的，劳动者申请仲裁不受本条第一款规定的仲裁时效期间限制。但其他争议（如工伤、年休假）仍适用1年时效。',
        noLimitation: true },
      { value: '劳动-报酬离职', label: '拖欠劳动报酬（离职后）', period: '1年', law: '劳动争议调解仲裁法第27条第4款',
        note: '劳动关系终止的，应当自劳动关系终止之日起一年内提出。注意起算点是"离职之日"，而非欠薪发生之日。' },
    ],
  },
  {
    value: '行政诉讼', label: '行政诉讼', period: '6个月 / 1年 / 5年 / 20年', law: '行政诉讼法第46条',
    subTypes: [
      { value: '行政-一般', label: '一般行政诉讼', period: '6个月', law: '行政诉讼法第46条第1款',
        note: '公民、法人或者其他组织直接向人民法院提起诉讼的，应当自知道或者应当知道作出行政行为之日起六个月内提出。' },
      { value: '行政-未告知诉权', label: '行政机关未告知诉权/起诉期限', period: '1年', law: '行政诉讼法第46条 + 最高法解释第65条',
        note: '行政机关作出行政行为时未告知公民、法人或者其他组织起诉期限的，起诉期限从公民、法人或者其他组织知道或者应当知道起诉期限之日起计算，但从知道或者应当知道行政行为内容之日起最长不得超过一年。' },
      { value: '行政-不动产', label: '涉及不动产的行政行为', period: '20年', law: '行政诉讼法第46条第2款',
        note: '因不动产提起诉讼的案件自行政行为作出之日起超过二十年，其他案件自行政行为作出之日起超过五年提起诉讼的，人民法院不予受理。起算点是"行政行为作出之日"，非"知道之日"。' },
      { value: '行政-其他最长', label: '其他行政案件（最长保护期）', period: '5年', law: '行政诉讼法第46条第2款',
        note: '非不动产案件自行政行为作出之日起超过五年提起诉讼的，人民法院不予受理。' },
    ],
  },
  {
    value: '行政复议', label: '行政复议', period: '60日', law: '行政复议法第9条',
    note: '自知道具体行政行为之日起六十日内提出行政复议申请。可因不可抗力等正当理由申请延长期限。',
  },
  {
    value: '国家赔偿', label: '国家赔偿', period: '2年', law: '国家赔偿法第39条',
    note: '赔偿请求人请求国家赔偿的时效为两年，自国家机关及其工作人员行使职权时的行为被依法确认为违法之日起算。被羁押期间不计算在内。若行为持续，自行为终止之日起算。',
  },
  {
    value: '保险', label: '保险理赔', period: '2年 / 5年', law: '保险法第26条',
    subTypes: [
      { value: '保险-非人寿', label: '人寿保险以外的其他保险', period: '2年', law: '保险法第26条第1款',
        note: '被保险人或者受益人向保险人请求赔偿或者给付保险金的诉讼时效期间为二年，自其知道或者应当知道保险事故发生之日起计算。' },
      { value: '保险-人寿', label: '人寿保险', period: '5年', law: '保险法第26条第2款',
        note: '人寿保险的被保险人或者受益人向保险人请求给付保险金的诉讼时效期间为五年，自其知道或者应当知道保险事故发生之日起计算。' },
    ],
  },
  {
    value: '票据', label: '票据追索权', period: '6个月 / 3个月', law: '票据法第17条',
    subTypes: [
      { value: '票据-追索', label: '票据追索权（持票人→前手）', period: '6个月', law: '票据法第17条第1项',
        note: '持票人对前手的追索权，自被拒绝承兑或者被拒绝付款之日起六个月不行使而消灭。' },
      { value: '票据-再追索', label: '票据再追索权（清偿人→其他前手）', period: '3个月', law: '票据法第17条第4项',
        note: '持票人行使追索权清偿债务后，对其前手的再追索权，自清偿日或者被提起诉讼之日起三个月不行使而消灭。' },
    ],
  },
  {
    value: '海商', label: '海上货物运输', period: '1年', law: '海商法第257条',
    note: '就海上货物运输向承运人要求赔偿的请求权，时效期间为一年，自承运人交付或者应当交付货物之日起计算。',
  },
]

// 二级子类型
const subTypeOptions = computed<SubTypeRule[]>(() => {
  const rule = allRules.find(r => r.value === caseType.value)
  return rule?.subTypes || []
})

const subTypeLabel = computed(() => {
  if (caseType.value === '劳动') return '争议情形'
  if (caseType.value === '行政诉讼') return '行政行为类型'
  if (caseType.value === '民事') return '时效类型'
  if (caseType.value === '保险') return '保险类型'
  if (caseType.value === '票据') return '追索类型'
  return '情形'
})

const currentSubTypeNote = computed(() => {
  if (!subType.value) return ''
  const sub = subTypeOptions.value.find(s => s.value === subType.value)
  return sub?.note || ''
})

const caseType = ref('')
const subType = ref('')
const eventDate = ref('')
const result = ref<{
  deadline?: string; days_remaining?: number; status?: string
  law_basis?: string; note?: string; warning?: string; error?: string
} | null>(null)

// 顶层 caseTypes 显示主类型
const caseTypes = computed(() => allRules.map(r => ({
  value: r.value,
  label: r.label,
  period: r.period,
})))

function onCaseTypeChange() {
  subType.value = ''
  result.value = null
  // 若只有单一规则（无 subTypes），直接计算；否则等用户选子类型
  const rule = allRules.find(r => r.value === caseType.value)
  if (rule && !rule.subTypes && eventDate.value) {
    calculate()
  }
}

function onOpen() {
  result.value = null
  caseType.value = ''
  subType.value = ''
  eventDate.value = ''
}

/**
 * 计算最终 case_type key：
 * - 有 subTypes 时使用 subType.value（如"劳动-报酬在职"）
 * - 无 subTypes 时使用 caseType.value（如"行政复议"）
 */
function resolveCaseTypeKey(): string {
  return subType.value || caseType.value
}

function resolveRule(): { law: string; note: string; noLimitation?: boolean } | null {
  const rule = allRules.find(r => r.value === caseType.value)
  if (!rule) return null
  if (rule.subTypes && rule.subTypes.length > 0) {
    const sub = rule.subTypes.find(s => s.value === subType.value)
    return sub ? { law: sub.law, note: sub.note, noLimitation: sub.noLimitation } : null
  }
  // 单一规则（如行政复议、海商、国家赔偿）
  return {
    law: rule.law,
    note: rule.note || '',
  }
}

function buildDisplayLabel(): string {
  const rule = allRules.find(r => r.value === caseType.value)
  if (!rule) return caseType.value
  if (rule.subTypes && subType.value) {
    const sub = rule.subTypes.find(s => s.value === subType.value)
    return sub ? `${rule.label} · ${sub.label}` : rule.label
  }
  return rule.label
}

async function calculate() {
  if (!caseType.value || !eventDate.value) return
  // 检查是否需要子类型
  const rule = allRules.find(r => r.value === caseType.value)
  if (rule?.subTypes && rule.subTypes.length > 0 && !subType.value) return

  const localRule = resolveRule()

  // 不受时效限制的特殊处理（劳动报酬在职期间）
  if (localRule?.noLimitation) {
    result.value = {
      status: '不受时效限制',
      law_basis: localRule.law,
      note: localRule.note,
      warning: '虽然不受时效限制，但建议尽早主张权利以避免证据灭失。离职后1年内仍可主张。',
    }
    return
  }

  try {
    const resp = await backend.calcLimitationPeriod(resolveCaseTypeKey(), eventDate.value)
    // 后端返回的 note 可能不如本地详细，用本地规则覆盖
    if (localRule) {
      resp.law_basis = localRule.law
      resp.note = localRule.note
    }
    result.value = resp
  } catch (e: any) {
    result.value = { error: e.message || '计算失败' }
    ElMessage.error('时效计算失败')
  }
}

function selectSubRule(rule: LimitationRule, sub: SubTypeRule) {
  caseType.value = rule.value
  subType.value = sub.value
  if (eventDate.value) calculate()
}

function addToCalendar() {
  if (result.value?.deadline) {
    const label = buildDisplayLabel()
    emit('add-to-calendar', result.value.deadline, `诉讼时效届满 - ${label}`)
    ElMessage.success('已添加到日历提醒')
    visible.value = false
  }
}
</script>

<style scoped>
.limitation-calc { padding: 0 4px; }

.lc-intro {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: var(--legal-text-muted);
  margin-bottom: 16px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--radius-sm);
  line-height: 1.5;
}
.lc-star { color: var(--legal-danger); }

.lc-form { margin-bottom: 16px; }

.lc-option-meta {
  float: right;
  color: var(--legal-text-muted);
  font-size: 12px;
}

.lc-subtype-note {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin-top: 6px;
  padding: 6px 10px;
  background: var(--legal-warning-bg);
  border-left: 2px solid var(--legal-warning);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--legal-text-secondary);
  line-height: 1.5;
}

/* 结果区域 */
.lc-result {
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid;
}
.lc-result.已过期 { background: rgba(245,108,108,0.06); border-color: rgba(245,108,108,0.3); }
.lc-result.紧急 { background: rgba(230,162,60,0.06); border-color: rgba(230,162,60,0.3); }
.lc-result.正常 { background: rgba(103,194,58,0.06); border-color: rgba(103,194,58,0.3); }
.lc-result.不受时效限制 {
  background: var(--legal-info-bg);
  border-color: var(--legal-info);
}

.lc-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.lc-result-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 16px;
  font-weight: 600;
}
.lc-result-days {
  font-size: 14px;
  font-weight: 600;
  color: var(--legal-navy);
}

.lc-result-deadline, .lc-result-law {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
}

.lc-result-label {
  color: var(--legal-text-muted);
  min-width: 70px;
  flex-shrink: 0;
}
.lc-result-value {
  color: var(--legal-text);
  font-weight: 500;
  flex: 1;
}
.lc-result-note {
  margin-top: 8px;
  font-size: 12px;
  color: var(--legal-text-secondary);
  line-height: 1.6;
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-extra-light);
}

.lc-result-warning {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin-top: 8px;
  padding: 6px 10px;
  background: var(--legal-warning-bg);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--legal-warning);
  line-height: 1.5;
}

/* 参考规则 */
.lc-reference { margin-top: 8px; }
.lc-rules-tree {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.lc-rule-group {
  padding: 8px 10px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--radius-sm);
}
.lc-rule-group-title {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
}
.lc-rule-name { font-size: 12px; font-weight: 600; color: var(--legal-text); }
.lc-rule-period { font-size: 11px; color: var(--legal-gold-dark); }
.lc-rule-law { font-size: 10px; color: var(--legal-text-muted); margin-left: auto; }
.lc-rule-subs {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 6px;
  padding-left: 8px;
}
.lc-rule-sub {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  padding: 4px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}
.lc-rule-sub:hover { background: var(--el-fill-color); }
.lc-rule-sub-name { font-size: 11px; color: var(--legal-text); }
.lc-rule-sub-period { font-size: 10px; color: var(--legal-gold-dark); }
.lc-rule-sub-law { font-size: 10px; color: var(--legal-text-muted); margin-left: auto; }
</style>
