<template>
  <div class="skill-page">
    <div class="sp-header">
      <div>
        <h2 class="page-title">法律技能库</h2>
        <p class="page-subtitle">聚焦法律实务的高频技能，点击即可调用</p>
      </div>
      <div class="sp-header-actions">
        <el-button size="small" text @click="showCustomDialog = true">
          <el-icon><Plus /></el-icon> 自定义技能
        </el-button>
      </div>
    </div>

    <!-- ═══ Recently / Most used ═══ -->
    <div v-if="skillStore.mostUsed.length > 0" class="sp-recent">
      <div class="sp-recent-header">
        <el-icon size="14"><Clock /></el-icon>
        <span>常用技能</span>
      </div>
      <div class="sp-recent-items">
        <div v-for="s in skillStore.mostUsed.slice(0, 4)" :key="s.id" class="sp-recent-chip" @click="showPreview(s)">
          <span>{{ s.icon }}</span>
          <span class="sp-recent-name">{{ s.name }}</span>
          <span class="sp-recent-count">{{ skillStore.getUsageCount(s.id) }}次</span>
        </div>
      </div>
    </div>

    <!-- ═══ Skill groups ═══ -->
    <div v-for="(groupSkills, group) in skillStore.getSkillsByGroup()" :key="group" class="sp-group">
      <h3 class="sp-group-title">{{ group }}</h3>
      <div class="sp-grid">
        <div
          v-for="skill in groupSkills" :key="skill.id"
          class="sp-card"
          @click="showPreview(skill)"
        >
          <div class="sp-card-icon" :style="{ background: skill.color + '18', color: skill.color }">
            <span>{{ skill.icon }}</span>
          </div>
          <div class="sp-card-body">
            <span class="sp-card-name">{{ skill.name }}</span>
            <span class="sp-card-desc">{{ skill.description }}</span>
          </div>
          <div class="sp-card-right">
            <span v-if="skillStore.getUsageCount(skill.id) > 0" class="sp-usage-badge">{{ skillStore.getUsageCount(skill.id) }}</span>
            <el-tag v-if="skill.rpcMethod" size="small" effect="plain" type="info" class="sp-rpc-tag">实时</el-tag>
            <el-button size="small" round class="sp-card-btn" @click.stop="invokeSkill(skill)">
              <el-icon><Lightning /></el-icon> {{ skill.rpcMethod ? '检索' : '调用' }}
            </el-button>
            <el-tooltip v-if="isCustomSkill(skill)" content="删除此自定义技能" placement="top">
              <el-icon class="sp-del" size="13" @click.stop="removeCustomSkill(skill)"><Delete /></el-icon>
            </el-tooltip>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ Skill Preview Dialog ═══ -->
    <el-dialog v-model="showPreviewDialog" :title="previewSkill?.name || '技能预览'" width="520px">
      <div v-if="previewSkill" class="sp-preview">
        <div class="sp-preview-header">
          <span class="sp-preview-icon" :style="{ background: previewSkill.color + '18', color: previewSkill.color }">{{ previewSkill.icon }}</span>
          <div class="sp-preview-info">
            <span class="sp-preview-name">{{ previewSkill.name }}</span>
            <span class="sp-preview-group">{{ previewSkill.group }}</span>
          </div>
        </div>
        <div class="sp-preview-desc">{{ previewSkill.description }}</div>
        <div v-if="previewSkill.prompt" class="sp-preview-section">
          <div class="sp-preview-label">技能提示词</div>
          <pre class="sp-preview-prompt">{{ previewSkill.prompt }}</pre>
        </div>
        <div v-if="previewSkill.rpcMethod" class="sp-preview-section">
          <div class="sp-preview-label">检索关键词</div>
          <el-input v-model="rpcQuery" placeholder="输入检索关键词..." :rows="2" type="textarea" />
          <div v-if="rpcResult" class="sp-preview-result" v-html="rpcResult"></div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showPreviewDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmInvoke">
          {{ previewSkill?.rpcMethod ? '开始检索' : '使用此技能' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- ═══ RPC result dialog (standalone) ═══ -->
    <el-dialog v-model="showRpcResult" title="检索结果" width="640px">
      <div class="sp-rpc-result" v-html="rpcResultWithSources"></div>
      <template #footer>
        <el-button @click="showRpcResult = false">关闭</el-button>
        <el-button v-if="rpcResultRaw" type="primary" @click="copyRpcResult">复制结果</el-button>
      </template>
    </el-dialog>

    <!-- ═══ Create Custom Skill Dialog ═══ -->
    <el-dialog v-model="showCustomDialog" title="自定义技能" width="480px">
      <el-form label-position="top">
        <el-form-item label="技能名称" required>
          <el-input v-model="customForm.name" placeholder="如：公司章程审查" />
        </el-form-item>
        <el-form-item label="Emoji 图标">
          <el-input v-model="customForm.icon" placeholder="默认 🛠️" maxlength="2" style="width:80px" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="customForm.description" placeholder="简短描述技能用途" />
        </el-form-item>
        <el-form-item label="分组">
          <el-select v-model="customForm.group" style="width:100%">
            <el-option v-for="g in skillStore.allGroups" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
        <el-form-item label="AI 提示词" required>
          <el-input v-model="customForm.prompt" type="textarea" :rows="5"
            placeholder="输入你希望 AI 遵循的提示词指令，如：请帮我审查以下合同中的风险条款：&#10;&#10;合同内容：" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCustomDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!customForm.name || !customForm.prompt" @click="saveCustomSkill">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Lightning, Plus, Clock, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { renderMarkdown } from '../lib/markdown'
import { copyText } from '../lib/clipboard'
import { useSkillStore } from '../stores/skill'
import { useChatStore } from '../stores/chat'
import { backend } from '../lib/backend'
import type { LegalSkill } from '../types/legal'

const emit = defineEmits<{
  'enter-chat': [sessionId: string]
}>()

const skillStore = useSkillStore()
const chatStore = useChatStore()

// ── Preview dialog ──
const showPreviewDialog = ref(false)
const previewSkill = ref<LegalSkill | null>(null)
const rpcQuery = ref('')
const rpcResult = ref('')
const rpcResultRaw = ref('')
const showRpcResult = ref(false)

function showPreview(skill: LegalSkill) {
  previewSkill.value = skill
  rpcQuery.value = ''
  rpcResult.value = ''
  showPreviewDialog.value = true
}

// ── Confirm invoke from preview ──
async function confirmInvoke() {
  if (!previewSkill.value) return
  const skill = previewSkill.value
  showPreviewDialog.value = false

  // RPC skill: execute directly
  if (skill.rpcMethod) {
    if (!rpcQuery.value.trim()) {
      ElMessage.warning('请输入检索关键词')
      return
    }
    await executeRpcSkill(skill)
    return
  }

  // Normal skill: navigate to chat with pre-filled prompt
  invokeSkill(skill)
}

// ── Direct RPC execution ──
async function executeRpcSkill(skill: LegalSkill) {
  const searchType = skill.searchType || (skill.id === 'case-search' ? 'case' : 'law')
  skillStore.recordUsage(skill.id)
  skillStore.recordRecent(skill.id)
  try {
    const result = await backend.legalSearch(rpcQuery.value.trim(), searchType)
    const results = (result?.results || []) as any[]
    let reply = ''
    if (results.length === 0) {
      reply = `未找到与"${rpcQuery.value}"相关的法律信息。`
    } else {
      reply = `## ${skill.name} 结果\n\n共找到 ${results.length} 条结果：\n\n`
      for (const r of results.slice(0, 10)) {
        reply += `- **${r.title || r.name || '未知'}**`
        if (r.case_no) reply += `（${r.case_no}）`
        else if (r.department || r.publish_date) reply += `（${r.department || ''} ${r.publish_date || ''}）`
        if (r.effective !== undefined) reply += ` ${r.effective ? '✅有效' : '❌已失效'}`
        reply += '\n'
        if (r.summary) reply += `  > ${String(r.summary).replace(/\s+/g, ' ').slice(0, 160)}\n`
      }
    }
    rpcResultRaw.value = reply
    rpcResult.value = renderMarkdown(reply)
    rpcResultWithSources.value = renderRpcResult(reply, results)
    showRpcResult.value = true
  } catch (e: any) {
    ElMessage.error(`检索失败: ${e.message || '未知错误'}`)
  }
}

const rpcResultWithSources = ref('')

function renderRpcResult(md: string, results: any[]): string {
  try {
    const html = renderMarkdown(md)
    if (results.length === 0) return html
    let sources = '<hr style="margin:16px 0"/><h4>数据来源</h4><ul style="font-size:12px;color:var(--legal-text-muted)">'
    const usedSources = new Set<string>()
    for (const r of results.slice(0, 10)) {
      if (r.source && !usedSources.has(r.source)) {
        sources += `<li>${r.source}</li>`
        usedSources.add(r.source)
      }
    }
    sources += '</ul>'
    return html + sources
  } catch { return md }
}

async function copyRpcResult() {
  if (rpcResultRaw.value) {
    ;(await copyText(rpcResultRaw.value)) ? ElMessage.success('已复制') : ElMessage.warning('复制失败')
  }
}

// ── Navigate to chat with skill ──
function invokeSkill(skill: LegalSkill) {
  skillStore.recordUsage(skill.id)
  skillStore.recordRecent(skill.id)
  chatStore.newSession()

  // If skill has a prompt template, use it as the pending prompt so ChatPanel pre-fills it
  if (skill.prompt) {
    chatStore.setPendingSkill({ id: skill.id, name: skill.name, icon: skill.icon, prompt: skill.prompt, rpcMethod: skill.rpcMethod })
  } else if (skill.rpcMethod) {
    // RPC with no prompt: just name the session
    chatStore.setPendingSkill({ id: skill.id, name: skill.name, icon: skill.icon, prompt: '', rpcMethod: skill.rpcMethod })
  } else {
    chatStore.setPendingSkill({ id: skill.id, name: skill.name, icon: skill.icon, prompt: '', rpcMethod: skill.rpcMethod })
  }

  emit('enter-chat', chatStore.activeSessionId!)
  ElMessage.success(`已调用「${skill.name}」`)
}

// ── Custom skill form ──
const showCustomDialog = ref(false)
const customForm = ref({
  name: '',
  icon: '🛠️',
  description: '',
  group: '其他',
  prompt: '',
})

function isCustomSkill(skill: LegalSkill): boolean {
  return skillStore.customSkills.some(s => s.id === skill.id)
}

function removeCustomSkill(skill: LegalSkill) {
  skillStore.removeCustomSkill(skill.id)
  ElMessage.success(`已删除自定义技能「${skill.name}」`)
}

function saveCustomSkill() {
  if (!customForm.value.name || !customForm.value.prompt) return
  skillStore.addCustomSkill({
    name: customForm.value.name,
    icon: customForm.value.icon || '🛠️',
    description: customForm.value.description || '',
    color: '#6b7280',
    group: customForm.value.group,
    prompt: customForm.value.prompt,
  })
  showCustomDialog.value = false
  customForm.value = { name: '', icon: '🛠️', description: '', group: '其他', prompt: '' }
  ElMessage.success('自定义技能已创建')
}

onMounted(() => {
  skillStore.fetchBackendSkills()
})
</script>

<style scoped>
.skill-page {
  padding: 24px 28px 40px;
  overflow: visible;    /* 外层 view-slot--page-scroll 统一提供唯一滚动条 */
  height: auto;
  min-height: 100%;
  max-width: 1000px;
  margin: 0 auto;
}

.page-title { margin: 0; font-size: 22px; color: var(--legal-navy); }
.page-subtitle { margin: 4px 0 0; color: var(--legal-text-secondary); font-size: 13px; }

.sp-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.sp-header-actions { display: flex; gap: 8px; flex-shrink: 0; }

/* ── Recent / Most used ── */
.sp-recent {
  background: var(--legal-gold-bg);
  border: 1px solid var(--legal-gold-lighter);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  margin-bottom: 24px;
}
.sp-recent-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--legal-gold-dark);
  margin-bottom: 8px;
}
.sp-recent-items {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.sp-recent-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 16px;
  background: var(--legal-bg-card);
  border: 1px solid var(--legal-gold-lighter);
  cursor: pointer;
  font-size: 12px;
  transition: all var(--transition-fast);
}
.sp-recent-chip:hover {
  border-color: var(--legal-gold);
  box-shadow: var(--shadow-sm);
}
.sp-recent-name { font-weight: 500; }
.sp-recent-count {
  font-size: 11px;
  color: var(--legal-text-muted);
  margin-left: 2px;
}

/* ── Groups ── */
.sp-group { margin-top: 28px; }
.sp-group-title {
  font-size: 14px; color: var(--legal-navy);
  margin: 0 0 12px; padding-bottom: 6px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

/* ── Grid ── */
.sp-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.sp-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.sp-card:hover {
  border-color: var(--legal-gold);
  box-shadow: var(--shadow-sm);
}

.sp-card-icon {
  width: 40px; height: 40px;
  border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.sp-card-body {
  flex: 1;
  min-width: 0;
}

.sp-card-name {
  font-size: 14px;
  font-weight: var(--weight-medium);
  color: var(--legal-text);
  display: block;
  margin-bottom: 2px;
}

.sp-card-desc {
  font-size: 12px;
  color: var(--legal-text-muted);
  line-height: 1.4;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;      /* 两行截断 + 省略号（描述较长，单行放不下） */
  -webkit-box-orient: vertical;
  word-break: break-all;
}

.sp-card-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}

.sp-card-btn {
  font-size: 12px;
  padding: 4px 10px;
}

.sp-usage-badge {
  font-size: 10px;
  background: var(--el-fill-color);
  color: var(--legal-text-muted);
  padding: 0 6px;
  border-radius: 8px;
  line-height: 16px;
}

.sp-del {
  cursor: pointer;
  opacity: 0.35;
  color: var(--legal-text-muted);
  transition: opacity var(--transition-fast), color var(--transition-fast);
}
.sp-del:hover {
  opacity: 1;
  color: var(--legal-danger);
}

.sp-rpc-tag {
  font-size: 10px !important;
  height: 18px;
  line-height: 16px;
}

/* ── Preview dialog ── */
.sp-preview { }
.sp-preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.sp-preview-icon {
  width: 48px; height: 48px;
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}
.sp-preview-info { display: flex; flex-direction: column; }
.sp-preview-name { font-size: 16px; font-weight: 600; color: var(--legal-navy); }
.sp-preview-group { font-size: 12px; color: var(--legal-text-muted); }
.sp-preview-desc {
  font-size: 13px;
  color: var(--legal-text-secondary);
  margin-bottom: 16px;
  line-height: 1.5;
}
.sp-preview-section { margin-bottom: 12px; }
.sp-preview-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--legal-text-muted);
  margin-bottom: 6px;
}
.sp-preview-prompt {
  font-size: 13px;
  background: var(--el-fill-color);
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  line-height: 1.6;
  white-space: pre-wrap;
  margin: 0;
  font-family: var(--font-ui);
}
.sp-preview-result {
  margin-top: 8px;
  padding: 10px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--radius-sm);
  font-size: 13px;
  line-height: 1.6;
}

/* ── RPC result dialog ── */
.sp-rpc-result {
  font-size: 14px;
  line-height: 1.7;
  max-height: 60vh;
  overflow-y: auto;
}

/* ── Custom skill form ── */
.sp-custom-field {
  margin-bottom: 12px;
}

/* ── Dark mode ── */
[data-theme="dark"] .sp-recent {
  background: rgba(212,168,67,0.08);
  border-color: rgba(212,168,67,0.2);
}
[data-theme="dark"] .sp-recent-chip {
  background: var(--legal-bg-card);
  border-color: var(--legal-border);
}
[data-theme="dark"] .sp-card {
  background: var(--legal-bg-card);
  border-color: var(--legal-border);
}
[data-theme="dark"] .sp-card:hover {
  border-color: var(--legal-gold-dark);
}
[data-theme="dark"] .sp-usage-badge {
  background: var(--el-fill-color);
}
</style>
