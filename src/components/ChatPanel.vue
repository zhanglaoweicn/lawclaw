<template>
  <div class="chat-panel">
    <!-- ═══════════ AG-UI Run Progress & Steps (P1) ═══════════ -->
    <Transition name="run-progress">
      <div v-if="chatStore.steps.length > 0" class="run-progress-wrap">
        <div class="run-progress-row" @click="showStepsExpanded = !showStepsExpanded">
          <div class="rp-left">
            <el-icon :size="15" :class="{ spin: chatStore.runInProgress }">
              <Loading v-if="chatStore.runInProgress" />
              <CircleCloseFilled v-else-if="chatStore.runFailed" style="color:var(--el-color-danger)" />
              <CircleCheckFilled v-else style="color:#2d7d4e" />
            </el-icon>
            <span class="rp-title">
              <template v-if="chatStore.runInProgress">正在处理（{{ chatStore.completedSteps }}/{{ chatStore.steps.length }} 步）</template>
              <template v-else-if="chatStore.runFailed">处理失败（共 {{ chatStore.steps.length }} 步）— 请查看下方错误提示</template>
              <template v-else>处理完成（共 {{ chatStore.steps.length }} 步）</template>
            </span>
          </div>
          <div class="rp-right">
            <el-progress
              :percentage="chatStore.runInProgress ? chatStore.runProgressPercent : 100"
              :stroke-width="6"
              :show-text="false"
              :color="chatStore.runInProgress ? 'var(--el-color-primary)' : (chatStore.runFailed ? 'var(--el-color-danger)' : '#2d7d4e')"
              style="width: 140px"
            />
            <el-icon :size="14" :class="{ rotated: showStepsExpanded }" style="margin-left:8px;color:var(--legal-muted)">
              <ArrowRight />
            </el-icon>
          </div>
        </div>
        <Transition name="step-list">
          <div v-if="showStepsExpanded" class="run-step-list">
            <div
              v-for="s in chatStore.steps"
              :key="s.stepId"
              :class="['run-step-item', `kind-${s.kind}`, `st-${s.status}`]"
            >
              <div class="rs-indicator">
                <el-icon :size="13" v-if="s.status === 'ok'"><CircleCheckFilled style="color:#2d7d4e" /></el-icon>
                <el-icon :size="13" v-else-if="s.status === 'running'" class="spin"><Loading style="color:var(--el-color-primary)" /></el-icon>
                <el-icon :size="13" v-else-if="s.status === 'failed'"><CircleClose style="color:var(--el-color-danger)" /></el-icon>
                <div v-else class="rs-skipped-dot"></div>
              </div>
              <div class="rs-body">
                <div class="rs-title-row">
                  <span class="rs-kind-tag">{{ kindLabel(s.kind) }}</span>
                  <span class="rs-title">{{ s.title }}</span>
                  <span class="rs-idx">#{{ s.stepIndex }}</span>
                </div>
                <div v-if="s.description" class="rs-desc">{{ s.description }}</div>
                <div v-if="s.kind === 'tool' && s.toolPreview" class="rs-tool-preview">
                  {{ s.toolPreview }}
                </div>
                <div v-if="s.finishedAt" class="rs-duration">
                  耗时 {{ stepDurationMs(s) }} ms
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>

    <div class="messages" ref="messagesRef" @scroll="onMessagesScroll">
      <!-- Welcome -->
      <div v-if="chatStore.messages.length === 0" class="welcome">
        <div class="welcome-icon">&#x2696;</div>
        <h2>{{ welcomeTitle }}</h2>
        <p class="welcome-desc">{{ welcomeDesc }}</p>
        <div class="welcome-grid">
          <div v-for="s in welcomeSkills" :key="s.id" class="wg-item" @click="pickSkill(s)">
            <span class="wg-icon">{{ s.icon }}</span>
            <span class="wg-label">{{ s.name }}</span>
          </div>
        </div>
        <div v-if="skills.length > 8" class="welcome-more">
          <span class="welcome-more-text">还有 {{ skills.length - 8 }} 个技能 · 前往技能页查看更多</span>
        </div>
        <div v-if="expertStore.favoriteRoles.length > 0" class="welcome-experts">
          <div class="welcome-expert-label">&#x2B50; 收藏专家</div>
          <div class="welcome-expert-items">
            <div v-for="fr in expertStore.favoriteRoles.slice(0, 3)" :key="fr.role.id" class="welcome-expert-chip" @click="pickExpertFromWelcome(fr.role, fr.group)">
              <span>{{ fr.role.icon }}</span>
              <span>{{ fr.role.name }}</span>
            </div>
          </div>
        </div>
        <div class="welcome-quick-replies">
          <div class="welcome-qr-label">快速开始</div>
          <div class="welcome-qr-grid">
            <div v-for="qr in quickReplies" :key="qr.text" class="welcome-qr-item" @click="sendQuickReply(qr.text)">
              <span>{{ qr.icon }}</span>
              <span class="welcome-qr-text">{{ qr.text }}</span>
            </div>
          </div>
        </div>
      </div>

      <template v-for="(msg, msgIdx) in chatStore.messages" :key="msg.id">
        <!-- Time group separator -->
        <div v-if="shouldShowDateSeparator(msgIdx)" class="msg-date-sep">
          <span class="msg-date-text">{{ messageDateGroup(msg.timestamp) }}</span>
        </div>
        <div :class="['msg-row', msg.role]">
          <div class="msg-avatar">
            <span>{{ msg.role === 'assistant' ? '&#x2696;' : '&#x1F464;' }}</span>
          </div>
          <div class="msg-body">
            <div class="msg-name">
              {{ msg.role === 'assistant' ? 'LawClaw' : '您' }}
              <span v-if="msg.role === 'assistant' && chatStore.activeSession?.expertRoleId" class="msg-role">· {{ currentExpertLabel }}</span>
            </div>
            <div :class="['msg-bubble', { 'msg-bubble-error': msg.error }]" v-html="renderMarkdown(msg.content)" />
            <div v-if="msg.role === 'assistant' && msg.contextStats && (msg.contextStats.history_rounds || msg.contextStats.kb_chunks || msg.contextStats.experience || msg.contextStats.files)"
                 class="msg-ctx-line"
                 title="上下文构成（前缀缓存友好：稳定系统提示 + 追加式历史 + 每轮注入置于消息尾部）">
              上下文：历史 {{ msg.contextStats.history_rounds || 0 }} 轮
              <template v-if="msg.contextStats.kb_chunks">· 案件文档 {{ msg.contextStats.kb_chunks }} 段</template>
              <template v-if="msg.contextStats.experience">· 相似经验 {{ msg.contextStats.experience }} 条</template>
              <template v-if="msg.contextStats.files">· 附件 {{ msg.contextStats.files }} 个</template>
            </div>
            <div v-if="msg.error" class="msg-error-hint">
              <el-icon size="12"><CircleClose /></el-icon>
              本次调用未成功 — 可直接重新发送，或到「配置」检查 API Key / 网络
            </div>
            <div v-if="msg.reasoning" class="msg-reasoning">
              <div class="msg-reasoning-header" @click="toggleReasoning(msg.id)">
                <el-icon size="12"><ArrowRight :class="{ rotated: expandedReasoning === msg.id }" /></el-icon>
                <span>推理过程</span>
              </div>
              <div v-if="expandedReasoning === msg.id" class="msg-reasoning-body" v-html="renderMarkdown(msg.reasoning)"></div>
            </div>
            <div v-if="msg.citations?.length" class="msg-citations">
              <div class="msg-cit-title">
                <span>引用来源（{{ msg.citations.length }}条）</span>
                <button class="msg-cit-copy" title="复制全部引用文本" @click="copyCitations(msg.citations)">
                  <el-icon size="11"><CopyDocument /></el-icon> 复制全部
                </button>
              </div>
              <CitationCard v-for="cite in msg.citations" :key="cite.article" :citation="cite" />
            </div>
            <div v-if="msg.role === 'user' && editingMessageId === msg.id" class="msg-edit-overlay">
              <el-input v-model="editMessageText" type="textarea" :rows="3" @keydown.enter.prevent="confirmEditMessage" />
              <div class="msg-edit-actions">
                <el-button size="small" text @click="cancelEditMessage">取消</el-button>
                <el-button size="small" type="primary" @click="confirmEditMessage">保存并重新发送</el-button>
              </div>
            </div>
            <div class="msg-foot">
              <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
              <span class="msg-tools">
                <template v-if="msg.role === 'user'">
                  <el-tooltip content="编辑" placement="top">
                    <el-button text size="small" class="msg-tool" @click="startEditMessage(msg)"><el-icon><Edit /></el-icon></el-button>
                  </el-tooltip>
                </template>
                <template v-if="msg.role === 'assistant'">
                  <el-tooltip content="保存为文书" placement="top">
                    <el-button text size="small" class="msg-tool" @click="showSaveDialog(msg)"><el-icon><DocumentAdd /></el-icon></el-button>
                  </el-tooltip>
                  <el-tooltip content="导出 Word 文档" placement="top">
                    <el-button text size="small" class="msg-tool" :loading="exportingMsgId === msg.id" @click="exportMsgDocx(msg)"><el-icon><Document /></el-icon></el-button>
                  </el-tooltip>
                  <el-tooltip content="复制" placement="top">
                    <el-button text size="small" class="msg-tool" @click="copyMessage(msg.content)"><el-icon><CopyDocument /></el-icon></el-button>
                  </el-tooltip>
                </template>
              </span>
            </div>
          </div>
        </div>
      </template>

      <div v-if="chatStore.loading && chatStore.runningSessionId === chatStore.activeSessionId" class="msg-row assistant">
        <div class="msg-avatar"><span>&#x2696;</span></div>
        <div class="msg-body">
          <div class="msg-name">LawClaw</div>
          <div class="typing-area">
            <div class="typing"><span class="td"></span><span class="td"></span><span class="td"></span></div>
            <el-button size="small" text class="abort-btn" @click="abortMessage">
              <el-icon><CircleClose /></el-icon> 停止
            </el-button>
          </div>
          <div v-if="chatStore.toolActivity" class="tool-activity-bar">
            <el-icon v-if="chatStore.toolActivity.status === 'running'" class="tool-spin"><Loading /></el-icon>
            <el-icon v-else color="var(--legal-success)"><CircleCheckFilled /></el-icon>
            <span class="tool-activity-text">
              {{ toolActivityLabel }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ 回到底部浮动按钮（用户向上滚动时显示） ═══ -->
    <Transition name="slide-up">
      <div v-if="userScrolledUp && chatStore.messages.length > 3" class="scroll-bottom-btn" @click="forceScrollToBottom">
        <el-icon><ArrowDownBold /></el-icon>
        <span>回到底部</span>
      </div>
    </Transition>

    <!-- ═══ File preview panel (between messages and input) ═══ -->
    <Transition name="slide-up">
      <div v-if="previewFile" class="preview-panel">
        <div class="pp-header">
          <span class="pp-name">{{ previewFile.name }}</span>
          <div class="pp-actions">
            <el-button v-if="isTextFile(previewFile.name) && !editing" text size="small" @click="startEdit">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button v-if="editing" text size="small" type="primary" @click="saveEdit">
              <el-icon><Check /></el-icon> 保存
            </el-button>
            <el-button v-if="editing" text size="small" @click="cancelEdit">
              <el-icon><Close /></el-icon> 取消
            </el-button>
            <el-button text size="small" @click="closePreview">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
        <div class="pp-body">
          <img v-if="isImageFile(previewFile.name) && !editing" :src="previewFile.data" class="pp-img" alt="预览" />
          <textarea v-else-if="editing" v-model="editText" class="pp-textarea" spellcheck="false"></textarea>
          <div v-else-if="isTextFile(previewFile.name)" class="pp-markdown" v-html="renderedPreview"></div>
          <div v-else class="pp-placeholder">
            <el-icon size="40"><Document /></el-icon>
            <p>{{ previewFile.name }}</p>
            <p class="pp-size">{{ formatFileSize(previewFile.data) }}</p>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ═══ Input card ═══ -->
    <div class="input-card">
      <!-- Active pills: skill + expert + case + attachments -->
      <div v-if="activeSkill || chatStore.activeSession?.expertRoleId || chatStore.activeSession?.matterId || attachedFiles.length" class="pills-line">
        <span v-if="activeSkill" class="pill pill-skill">
          <span class="pill-icon">{{ activeSkill.icon }}</span>
          <span>{{ activeSkill.name }}</span>
          <el-icon class="pill-x" size="12" @click.stop="clearSkill"><Close /></el-icon>
        </span>
        <span v-if="chatStore.activeSession?.expertRoleId" class="pill pill-expert">
          <el-icon size="12"><UserFilled /></el-icon>
          <span>{{ currentExpertLabel }}</span>
          <el-icon class="pill-x" size="12" @click.stop="clearExpert"><Close /></el-icon>
        </span>
        <span v-if="chatStore.activeSession?.matterId" class="pill pill-case">
          <el-icon size="12"><Files /></el-icon>
          <span>{{ currentCaseLabel }}</span>
        </span>
        <span v-for="(af, i) in attachedFiles" :key="i" class="pill pill-file" @click="openFilePreview(af, i)">
          <span class="pf-dot" :class="attachTypeClass(af.name)"></span>
          <span>{{ af.name }}</span>
          <el-tooltip content="保存到案件文件" placement="top">
            <el-icon class="pill-save" size="12" @click.stop="saveAttachedFile(i)"><FolderOpened /></el-icon>
          </el-tooltip>
          <el-icon class="pill-x" size="12" @click.stop="removeAttach(i)"><Close /></el-icon>
        </span>
      </div>

      <!-- Composer：输入框 + 发送按钮同行 -->
      <div class="composer-row">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          :autosize="{ minRows: 2, maxRows: 6 }"
          :placeholder="skillPlaceholder"
          :disabled="chatStore.loading"
          class="chat-input"
          @keydown.enter.exact="onEnterKey"
        />
        <el-tooltip content="发送（Enter）" placement="top">
          <button class="composer-send" :disabled="!inputText.trim() || chatStore.loading" @click="sendMessage">
            <el-icon><Promotion /></el-icon>
          </button>
        </el-tooltip>
      </div>

      <!-- Bottom toolbar: 4 buttons + hint -->
      <div class="toolbar-row">
        <div class="trl-left">
          <!-- Skill -->
          <el-popover :visible="showSkillPopover" trigger="click" :width="400" popper-class="sp-panel" @show="onSkillPanelOpen" @hide="showSkillPopover = false">
            <template #reference>
              <button class="tb-btn" :class="{ active: !!activeSkill }" :disabled="chatStore.loading" @click.stop="showSkillPopover = !showSkillPopover">
                <el-icon><Lightning /></el-icon><span>技能</span>
              </button>
            </template>
            <div class="sp-body">
              <div class="sp-search"><el-input v-model="skillSearch" size="small" placeholder="搜索技能..." :prefix-icon="Search" clearable /></div>
              <div class="sp-scroll">
                <template v-for="(sks, grp) in groupedSkills" :key="grp">
                  <div class="sp-group-title-row">{{ grp }}</div>
                  <div class="sp-grid">
                    <div v-for="s in sks" :key="s.id" class="sp-item" @click="pickSkill(s)">
                      <span class="sp-icon">{{ s.icon }}</span><span class="sp-name">{{ s.name }}</span>
                    </div>
                  </div>
                </template>
                <div v-if="filteredSkills.length === 0" class="sp-empty">无匹配技能</div>
              </div>
            </div>
          </el-popover>

          <!-- Expert -->
          <el-popover :visible="showExpertPopover" trigger="click" :width="380" popper-class="ep-panel" @show="onExpertPanelOpen" @hide="showExpertPopover = false">
            <template #reference>
              <button class="tb-btn" :class="{ active: !!chatStore.activeSession?.expertRoleId }" :disabled="chatStore.loading" @click.stop="showExpertPopover = !showExpertPopover">
                <el-icon><UserFilled /></el-icon><span>专家</span>
              </button>
            </template>
            <div class="ep-body">
              <div class="ep-tabs">
                <button v-for="cat in expertCategories" :key="cat.key" :class="['ep-tab', { active: activeExpertCat === cat.key }]" @click="activeExpertCat = cat.key">{{ cat.icon }} {{ cat.name }}</button>
              </div>
              <div class="ep-groups" ref="epGroupsRef">
                <div v-for="group in filteredExpertGroups" :key="group.id" class="ep-g">
                  <div class="ep-g-title">{{ group.icon }} {{ group.name }}</div>
                  <div class="ep-g-roles">
                    <div v-for="r in group.roles" :key="r.id" :class="['ep-r', { active: chatStore.activeSession?.expertRoleId === r.id }]" @click="pickExpert(r, group)">
                      <el-icon class="ep-r-star" size="11" @click.stop="expertStore.toggleFavorite(r.id)">
                        <StarFilled v-if="expertStore.isFavorite(r.id)" />
                        <Star v-else />
                      </el-icon>
                      <span class="ep-r-icon" :style="{ background: r.color + '18', color: r.color }">{{ r.icon }}</span>
                      <div class="ep-r-body">
                        <span class="ep-r-name">{{ r.name }}</span>
                        <span class="ep-r-desc">{{ r.description }}</span>
                      </div>
                      <span v-if="expertStore.getUsage(r.id) > 0" class="ep-r-usage">{{ expertStore.getUsage(r.id) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="chatStore.activeSession?.expertRoleId" class="ep-clear" @click="clearExpert"><el-icon><Close /></el-icon> 退出专家模式</div>
            </div>
          </el-popover>

          <!-- Case -->
          <el-popover :visible="showCasePopover" trigger="click" :width="320" popper-class="mp-panel" @show="onCasePanelOpen" @hide="showCasePopover = false">
            <template #reference>
              <button class="tb-btn" :class="{ active: !!chatStore.activeSession?.matterId }" :disabled="chatStore.loading" @click.stop="showCasePopover = !showCasePopover">
                <el-icon><Files /></el-icon><span>案件</span>
              </button>
            </template>
            <div class="mp-body">
              <div class="mp-search"><el-input v-model="caseSearch" size="small" placeholder="搜索案件..." :prefix-icon="Search" clearable /></div>
              <div class="mp-list" ref="mpListRef">
                <div v-for="m in filteredMatters" :key="m.id" :class="['mp-item', { active: m.id === chatStore.activeSession?.matterId }]" @click="pickCase(m.id)">
                  <span class="mp-dot" :style="{ background: stageColor(m.stage) }"></span>
                  <div class="mp-body"><span class="mp-title">{{ m.title }}</span><span class="mp-meta">{{ m.client }} · {{ m.stage }}</span></div>
                </div>
                <div v-if="filteredMatters.length === 0" class="sp-empty">无匹配案件</div>
              </div>
              <div v-if="chatStore.activeSession?.matterId" class="mp-clear" @click="pickCase('clear-case')"><el-icon><Close /></el-icon> 取消关联</div>
            </div>
          </el-popover>

          <!-- File -->
          <input ref="fileInputRef" type="file" multiple style="display:none" @change="onFileSelected" />
          <button class="tb-btn" :class="{ active: attachedFiles.length > 0 }" :disabled="chatStore.loading" @click="fileInputRef?.click()">
            <el-icon><Paperclip /></el-icon><span>文件</span>
          </button>
        </div>

        <div class="trl-right">
          <el-tooltip content="导出对话" placement="top">
            <el-button text size="small" class="tb-btn" @click="exportConversation">
              <el-icon><Download /></el-icon>
            </el-button>
          </el-tooltip>
          <span class="trl-hint">Enter 发送 · Shift+Enter 换行</span>
        </div>
      </div>
    </div>

    <!-- Save as Document Dialog -->
    <el-dialog v-model="showSaveAsDoc" title="保存为案件文书" width="460px">
      <el-form label-position="top">
        <el-form-item label="文书名称">
          <el-input v-model="saveDocName" placeholder="输入文书名称" />
        </el-form-item>
        <el-form-item label="所属案件" required>
          <el-select v-model="saveDocMatterId" placeholder="选择案件" style="width:100%">
            <el-option v-for="m in matterStore.matters" :key="m.id" :label="m.title" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="文件分类">
          <el-select v-model="saveDocCategory" placeholder="选择分类" style="width:100%">
            <el-option v-for="c in availableSaveCategories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveAsDoc = false">取消</el-button>
        <el-button type="primary" :disabled="!saveDocName || !saveDocMatterId" @click="confirmSaveDoc">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, computed, onMounted, watch } from 'vue'
import { backend } from '../lib/backend'
import {
  Lightning, UserFilled, Files, Paperclip, Close, Document,
  CopyDocument, DocumentAdd, Promotion, Search, Edit, Check, FolderOpened,
  StarFilled, Star, CircleClose, Download, ArrowRight, Loading, CircleCheckFilled,
  CircleCloseFilled, ArrowDownBold,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { exportMarkdownAsDocx } from '../lib/docxExport'
import { renderMarkdown } from '../lib/markdown'
import { copyText } from '../lib/clipboard'
import { useChatStore } from '../stores/chat'
import { useMatterStore } from '../stores/matter'
import { useFileStore } from '../stores/fileStore'
import { useSetupStore } from '../stores/setup'
import { useExpertStore } from '../stores/expert'
import { useSkillStore } from '../stores/skill'
import { stageColor } from '../lib/caseConstants'
import { dataUrlToText, textToDataUrl } from '../lib/encoding'
import CitationCard from './CitationCard.vue'
import type { Message, LegalSkill, ExpertCategory } from '../types/legal'
import type { RunStep } from '../stores/chat'

const chatStore = useChatStore()
const matterStore = useMatterStore()
const fileStore = useFileStore()
const setupStore = useSetupStore()
const expertStore = useExpertStore()
const skillStore = useSkillStore()

const inputText = ref('')
const messagesRef = ref<HTMLElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const attachedFiles = ref<{ name: string; data: string }[]>([])
/** Currently activated skill (not prompt text — the skill itself) */
const activeSkill = ref<LegalSkill | null>(null)
/** AG-UI Run steps 展开状态 */
const showStepsExpanded = ref(true)
/** Step kind → 中文标签 */
function kindLabel(k: string) {
  switch (k) {
    case 'tool': return '工具'
    case 'think': return '推理'
    case 'reply': return '回复'
    case 'final': return '总结'
    default: return k
  }
}
/** Step 耗时计算（ms 级） */
function stepDurationMs(s: RunStep) {
  try {
    const a = new Date(s.startedAt).getTime()
    const b = new Date(s.finishedAt!).getTime()
    if (b <= a || Number.isNaN(b) || Number.isNaN(a)) return '<1'
    return (b - a)
  } catch {
    return '?'
  }
}

// ── File preview state ──
const previewFile = ref<{ name: string; data: string } | null>(null)
const editing = ref(false)
const editText = ref('')
const renderedPreview = ref('')
const editingMessageId = ref<string | null>(null)
const editMessageText = ref('')

const skills = computed(() => skillStore.skills)
const welcomeSkills = computed(() => skills.value.slice(0, 8))

// ── Popover visibility ──
const showSkillPopover = ref(false)
const showExpertPopover = ref(false)
const showCasePopover = ref(false)
const skillSearch = ref('')
const caseSearch = ref('')
const activeExpertCat = ref<ExpertCategory>('litigation')
const spGridRef = ref<HTMLElement | null>(null)
const epGroupsRef = ref<HTMLElement | null>(null)
const mpListRef = ref<HTMLElement | null>(null)

const filteredSkills = computed(() => {
  const q = skillSearch.value.toLowerCase().trim()
  if (!q) return skills.value
  return skills.value.filter(s => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q))
})

const groupedSkills = computed(() => {
  const map: Record<string, typeof skills.value> = {}
  for (const s of filteredSkills.value) {
    if (!map[s.group]) map[s.group] = []
    map[s.group].push(s)
  }
  return map
})

const skillPlaceholder = computed(() => {
  if (chatStore.loading) return '思考中...'
  if (activeSkill.value) {
    if (activeSkill.value.rpcMethod) return `输入关键词进行${activeSkill.value.name}...`
    return `已启用「${activeSkill.value.name}」，输入内容后发送`
  }
  return '输入法律问题...'
})

const expertCategories = [
  { key: 'litigation' as const, icon: '⚖️', name: '诉讼' },
  { key: 'industry' as const, icon: '🏢', name: '行业' },
  { key: 'corporate' as const, icon: '🏛️', name: '公司' },
]

const filteredExpertGroups = computed(() => expertStore.getGroupsByCategory(activeExpertCat.value))

const filteredMatters = computed(() => {
  const q = caseSearch.value.toLowerCase().trim()
  if (!q) return matterStore.matters
  return matterStore.matters.filter(m => m.title.toLowerCase().includes(q) || m.client.toLowerCase().includes(q))
})

function onSkillPanelOpen() {
  skillSearch.value = ''
  nextTick(() => {
    const inp = spGridRef.value?.parentElement?.querySelector('.sp-search input') as HTMLInputElement
    inp?.focus()
  })
}
function onExpertPanelOpen() {
  activeExpertCat.value = 'litigation'
}
function onCasePanelOpen() {
  caseSearch.value = ''
  nextTick(() => {
    const inp = mpListRef.value?.parentElement?.querySelector('.mp-search input') as HTMLInputElement
    inp?.focus()
  })
}

function pickSkill(skill: LegalSkill) {
  showSkillPopover.value = false
  activeSkill.value = skill
  ElMessage.success(`已启用技能「${skill.name}」，输入您的问题后发送`)
  nextTick(() => {
    const ta = document.querySelector('.chat-input textarea') as HTMLTextAreaElement
    ta?.focus()
  })
}

function clearSkill() {
  activeSkill.value = null
}

function pickExpert(role: { id: string; name: string; systemPrompt: string; samplePrompt?: string }, group: any) {
  showExpertPopover.value = false
  chatStore.setExpertRole(role)
  // 示例问题直接填入输入框（不自动发送——由用户确认/补充后发出）
  if (role.samplePrompt) inputText.value = role.samplePrompt
  expertStore.recordUsage(role.id)
  ElMessage.success(`已召唤「${role.name}」`)
}

function pickExpertFromWelcome(role: any, group: any) {
  chatStore.setExpertRole(role)
  if (role.samplePrompt) inputText.value = role.samplePrompt
  expertStore.recordUsage(role.id)
  ElMessage.success(`已召唤「${role.name}」`)
}

function pickCase(id: string) {
  showCasePopover.value = false
  if (id === 'clear-case') {
    if (chatStore.activeSession) chatStore.activeSession.matterId = undefined
    ElMessage.success('已取消关联')
    return
  }
  const matter = matterStore.matters.find(m => m.id === id)
  if (matter && chatStore.activeSession) {
    chatStore.activeSession.matterId = id
    ElMessage.success(`已关联「${matter.title}」`)
  }
}

function clearExpert() {
  chatStore.clearExpertRole()
  const s = chatStore.activeSession
  if (s) { s.systemPrompt = undefined; s.expertRoleId = undefined }
  showExpertPopover.value = false
  ElMessage.success('已退出专家模式')
}

function messageDateGroup(date: Date): string {
  // UX-3 修复：用日期字符串比较代替 getDate() 数学计算，正确处理跨月跨年
  const now = new Date()
  const d = new Date(date)
  const dayMs = 86400000
  const diff = now.getTime() - d.getTime()

  // 标准化到 yyyy-mm-dd 比较
  const todayStr = now.toDateString()
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  const yesterdayStr = yesterday.toDateString()
  const dStr = d.toDateString()

  if (dStr === todayStr) return '今天'
  if (dStr === yesterdayStr) return '昨天'
  if (diff < 7 * dayMs) return d.toLocaleDateString('zh-CN', { weekday: 'long' })
  return d.toLocaleDateString('zh-CN')
}

function shouldShowDateSeparator(idx: number): boolean {
  if (idx === 0) return true
  const prev = chatStore.messages[idx - 1]
  const curr = chatStore.messages[idx]
  if (!prev || !curr) return false
  const prevDate = new Date(prev.timestamp).toDateString()
  const currDate = new Date(curr.timestamp).toDateString()
  return prevDate !== currDate
}

const expandedReasoning = ref<string | null>(null)

const welcomeTitle = computed(() => {
  const role = chatStore.activeSession?.expertRoleId
  if (!role) return '您好，我是 LawClaw'
  const r = expertStore.findRole(role)
  return r ? r.name : '您好，我是 LawClaw'
})

const toolActivityLabel = computed(() => {
  const ta = chatStore.toolActivity
  if (!ta) return ''
  const name = ta.name || ''
  // Human-readable labels for common legal tools
  const labelMap: Record<string, string> = {
    'mcp_yuandian_law_yuandian_rh_ft_search': '检索法律法规数据库',
    'mcp_yuandian_case_yuandian_rh_ft_search': '检索案例数据库',
    'mcp_yuandian_company_yuandian_rh_ft_search': '查询企业信息',
    'legal_search': '检索法律条文',
    'verify_citation': '验证法条有效性',
  }
  const label = labelMap[name] || (name.startsWith('mcp_yuandian') ? '检索法律数据库' : name)
  return ta.status === 'running' ? `${label}...` : `${label} 完成`
})

const welcomeDesc = computed(() => {
  const role = chatStore.activeSession?.expertRoleId
  if (!role) return '您的 AI 律师助理，选择技能或直接输入法律问题。'
  const r = expertStore.findRole(role)
  return r ? r.description : '您的 AI 律师助理'
})

const quickReplies = computed(() => {
  const base = [
    { icon: '📖', text: '查询民法典关于违约金的规定' },
    { icon: '📋', text: '帮我审查一份合同的重点条款' },
  ]
  const session = chatStore.activeSession
  if (session?.expertRoleId && session?.systemPrompt) {
    return [
      { icon: '🎯', text: '请根据当前案件事实进行分析' },
      { icon: '📝', text: '根据上面讨论的内容起草一份法律文书' },
      ...base,
    ]
  }
  if (session?.matterId) {
    return [
      { icon: '⚖️', text: '分析案件的诉讼策略' },
      { icon: '📋', text: '列出需要收集的证据清单' },
      ...base,
    ]
  }
  return base
})

const currentExpertLabel = computed(() => {
  const roleId = chatStore.activeSession?.expertRoleId
  if (!roleId) return '通用助理'
  const r = expertStore.findRole(roleId)
  return r ? r.name : '通用助理'
})

const currentCaseLabel = computed(() => {
  const mid = chatStore.activeSession?.matterId
  if (!mid) return '案件'
  const m = matterStore.matters.find(x => x.id === mid)
  return m ? m.title.slice(0, 18) + (m.title.length > 18 ? '…' : '') : '案件'
})

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || chatStore.loading) return

  const skill = activeSkill.value
  activeSkill.value = null
  inputText.value = ''
  scrollToBottom()  // 用户消息即将入列，立即贴底（等待 run 期间也能看到思考动画）

  // ── RPC skill: call backend legal_search API directly ──
  if (skill?.rpcMethod) {
    try {
      const searchType = skill.id === 'case-search' ? 'case' : 'law'
      const result = await backend.legalSearch(text, searchType)
      const results = (result?.results || []) as any[]
      let reply = ''
      if (results.length === 0) {
        reply = `未找到与"${text}"相关的法律信息。`
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
      chatStore.messages.push({
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
        role: 'user',
        content: text,
        timestamp: new Date(),
      })
      chatStore.messages.push({
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
        role: 'assistant',
        content: reply,
        timestamp: new Date(),
      })
    } catch (e: any) {
      chatStore.messages.push({
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
        role: 'assistant',
        content: `检索失败：${e.message || '未知错误'}`,
        timestamp: new Date(),
      })
    }
    chatStore.saveCurrentMessages()
    // Update session messageCount for RPC skills
    const curSession = chatStore.activeSession
    if (curSession) {
      curSession.messageCount = chatStore.messages.filter(m => m.role === 'user').length
      curSession.updatedAt = new Date()
    }
    scrollToBottom()
    return
  }

  // ── Normal chat skill or plain message ──
  // 技能工作流由后端通过 skill_id 注入完整 SKILL.md，前端只发送用户输入
  let fullText = text
  const currentFiles = [...attachedFiles.value]
  if (attachedFiles.value.length) {
    fullText = fullText + '\n\n---\n附件：\n' + attachedFiles.value.map(f => `[附件: ${f.name}]`).join('\n')
  }
  attachedFiles.value = []
  await chatStore.sendMessage(fullText, setupStore.apiKey, setupStore.baseUrl, setupStore.model, skill?.id, currentFiles)
  scrollToBottom()
}

/** Enter 发送；IME 组合中（拼音选词确认）的回车不触发 */
function onEnterKey(e: KeyboardEvent) {
  if (e.isComposing || e.keyCode === 229) return
  e.preventDefault()
  sendMessage()
}

function abortMessage() {
  chatStore.abortCurrentMessage(setupStore.apiKey, setupStore.baseUrl, setupStore.model)
}

/** 文档依赖型快速提示的门控：没有可用文档时不直接发送，引导上传/粘贴 */
function needsContractDocument(text: string): boolean {
  if (!/审查.{0,6}合同|合同.{0,6}审查|审阅.{0,4}合同/.test(text)) return false
  const hasAttached = attachedFiles.value.length > 0
  if (hasAttached) return false
  const matterId = chatStore.activeSession?.matterId || matterStore.activeMatterId
  if (!matterId) return true
  // 关联案件的已解析文档里找合同类文件
  return !fileStore.files.some(
    f => f.matterId === matterId && f.extractedText && /合同|协议|contract/i.test(f.name + ' ' + f.extractedText.slice(0, 800))
  )
}

function sendQuickReply(text: string) {
  // “审查合同”类提示词依赖合同文本——无文档时先引导上传/粘贴，避免空跑工作流
  if (needsContractDocument(text)) {
    inputText.value = text
    ElMessage.info('审查合同需要先提供合同文本：点击 📎 上传合同文件，或直接粘贴合同内容后发送')
    nextTick(() => fileInputRef.value?.click())   // 自动打开文件选择器（用户手势内）
    return
  }
  inputText.value = text
  nextTick(() => sendMessage())
}

function startEditMessage(msg: Message) {
  if (msg.role !== 'user') return
  editingMessageId.value = msg.id
  editMessageText.value = msg.content
}

function confirmEditMessage() {
  if (!editingMessageId.value || !editMessageText.value.trim()) return
  const id = editingMessageId.value
  editingMessageId.value = null
  chatStore.editMessage(id, editMessageText.value.trim())
  // Re-send the edited message
  inputText.value = editMessageText.value
  nextTick(() => sendMessage())
}

function cancelEditMessage() {
  editingMessageId.value = null
}

function toggleReasoning(id: string) {
  expandedReasoning.value = expandedReasoning.value === id ? null : id
}

function exportConversation() {
  const msgs = chatStore.messages
  if (msgs.length === 0) {
    ElMessage.warning('暂无消息可导出')
    return
  }
  let md = `# LawClaw 对话记录\n\n`
  md += `会话: ${chatStore.activeSession?.title || '未命名'}\n`
  md += `时间: ${new Date().toLocaleString('zh-CN')}\n`
  md += `消息数: ${msgs.length} 条\n\n---\n\n`
  for (const msg of msgs) {
    const role = msg.role === 'user' ? '**您**' : '**LawClaw**'
    md += `### ${role} (${formatTime(msg.timestamp)})\n\n${msg.content}\n\n`
    if (msg.citations?.length) {
      md += `引用来源:\n`
      for (const c of msg.citations) {
        md += `- ${c.law} ${c.article}: ${c.content}\n`
      }
      md += '\n'
    }
  }

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const sessionTitle = chatStore.activeSession?.title?.replace(/[/\\?%*:|"<>]/g, '_') || '对话记录'
  a.download = `LawClaw_${sessionTitle}_${new Date().toISOString().slice(0, 10)}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('对话已导出')
}

function attachTypeClass(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  if (['pdf'].includes(ext)) return 'at-pdf'
  if (['doc', 'docx', 'wps'].includes(ext)) return 'at-doc'
  if (['xls', 'xlsx', 'csv'].includes(ext)) return 'at-sheet'
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return 'at-image'
  if (['md', 'txt'].includes(ext)) return 'at-text'
  return 'at-other'
}

function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  for (const file of Array.from(input.files)) {
    const reader = new FileReader()
    reader.onload = (ev) => attachedFiles.value.push({ name: file.name, data: ev.target?.result as string })
    reader.readAsDataURL(file)
  }
  input.value = ''
}

function removeAttach(idx: number) {
  const removed = attachedFiles.value[idx]
  if (previewFile.value && previewFile.value.name === removed.name) {
    previewFile.value = null
    editing.value = false
  }
  attachedFiles.value.splice(idx, 1)
}

function saveAttachedFile(idx: number) {
  const af = attachedFiles.value[idx]
  if (!af) return
  const session = chatStore.activeSession
  if (!session?.matterId) {
    ElMessage.warning('请先关联案件后再保存附件')
    return
  }
  import('../stores/fileStore').then(({ useFileStore }) => {
    const fs = useFileStore()
    const category = fs.suggestCategory(af.name, session.matterId!)
    fs.addFile(af.name, af.data, '', category, session.matterId!)
      .then(() => ElMessage.success(`文件已保存到案件文件「${category}」`))
      .catch(() => ElMessage.error('文件保存失败'))
  })
}

// ── File preview functions ──
function openFilePreview(file: { name: string; data: string }, idx: number) {
  previewFile.value = file
  editing.value = false
  if (isTextFile(file.name)) {
    // UTF-8 安全解码（裸 atob 中文乱码）
    const raw = dataUrlToText(file.data)
    renderedPreview.value = renderMarkdown(raw)
    editText.value = raw
  }
}
function isImageFile(name: string) { return /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(name) }
function isTextFile(name: string) { return /\.(md|txt|markdown|json|xml|yaml|yml|csv|ts|js|vue)$/i.test(name) }
function startEdit() { editing.value = true }
function cancelEdit() { editing.value = false }
function saveEdit() {
  if (!previewFile.value) return
  // UTF-8 安全编码（btoa 直编码中文会抛 RangeError）
  const newData = textToDataUrl(editText.value, 'text/plain')
  previewFile.value.data = newData
  renderedPreview.value = renderMarkdown(editText.value)
  // Update the attached file data in place
  const idx = attachedFiles.value.findIndex(f => f.name === previewFile.value?.name)
  if (idx !== -1) attachedFiles.value[idx].data = newData
  editing.value = false
  ElMessage.success('已保存')
}
function closePreview() { previewFile.value = null; editing.value = false }

// ── UX-1: 智能滚动 ──
// 当用户向上滚动阅读历史时，暂停自动滚动到底部
// 当用户滚回接近底部时，恢复自动滚动
const userScrolledUp = ref(false)

function onMessagesScroll() {
  if (!messagesRef.value) return
  const el = messagesRef.value
  // 距离底部 < 80px 视为"在底部"
  const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  userScrolledUp.value = distanceFromBottom > 80
}

function scrollToBottom() {
  // 如果用户主动向上滚动了，不强制拉回底部
  if (userScrolledUp.value) return
  nextTick(() => { if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight })
}

function forceScrollToBottom() {
  userScrolledUp.value = false
  nextTick(() => { if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight })
}

function formatFileSize(data: string) {
  const bytes = Math.round((data.length * 3) / 4)
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

const showSaveAsDoc = ref(false)
const saveDocName = ref('')
const saveDocMatterId = ref('')
const saveDocCategory = ref('AI生成')
const saveTargetMsg = ref<Message | null>(null)
const availableSaveCategories = computed(() => {
  if (!saveDocMatterId.value) return ['AI生成', '案件文书', '证据材料']
  return ['AI生成', ...matterStore.categoriesForMatter(saveDocMatterId.value)]
})

function showSaveDialog(msg: Message) {
  saveTargetMsg.value = msg
  const firstLine = msg.content.split('\n')[0].replace(/^#+\s*/, '').slice(0, 40)
  saveDocName.value = firstLine || 'AI 生成文书'
  saveDocMatterId.value = matterStore.activeMatterId || ''
  saveDocCategory.value = 'AI生成'
  showSaveAsDoc.value = true
}

async function confirmSaveDoc() {
  if (!saveTargetMsg.value || !saveDocName.value || !saveDocMatterId.value) return
  const blob = new Blob([saveTargetMsg.value.content], { type: 'text/plain' })
  const reader = new FileReader()
  reader.onload = async () => {
    const name = saveDocName.value.endsWith('.md') ? saveDocName.value : saveDocName.value + '.md'
    await fileStore.addFile(name, reader.result as string, 'text/markdown', saveDocCategory.value as any, saveDocMatterId.value)
    ElMessage.success(`文书已保存`)
    showSaveAsDoc.value = false
  }
  reader.readAsDataURL(blob)
}

async function copyMessage(text: string) {
  (await copyText(text)) ? ElMessage.success('已复制') : ElMessage.warning('复制失败')
}

/** 复制一条消息的全部引用（逐条一行，可直接粘贴进文书） */
async function copyCitations(cites: Array<{ law: string; article: string; content: string }>) {
  const text = cites
    .map(c => `《${c.law}》${c.article}：${c.content.replace(/^《[^》]*》/, '').trim() || c.content}`)
    .join('\n')
  navigator.clipboard.writeText(text)
    .then(() => ElMessage.success(`已复制 ${cites.length} 条引用`))
    .catch(() => ElMessage.warning('复制失败'))
}

// ── AI 回复一键导出 Word（法律文书格式：宋体/黑体/首行缩进） ──
const exportingMsgId = ref<string | null>(null)

async function exportMsgDocx(msg: { id: string; content: string }) {
  if (exportingMsgId.value) return
  exportingMsgId.value = msg.id
  try {
    const matter = matterStore.matters.find(m => m.id === matterStore.activeMatterId)
    await exportMarkdownAsDocx('法律分析意见', msg.content, matter?.title || '')
    ElMessage.success('已导出 Word 文档')
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败（需要后端引擎运行）')
  } finally {
    exportingMsgId.value = null
  }
}

onMounted(() => {
  // Check for pending skill (from SkillPage invoke) — shows pill + prompt 模板预填输入框
  const pendingSkill = chatStore.consumePendingSkill()
  if (pendingSkill) {
    activeSkill.value = { id: pendingSkill.id, name: pendingSkill.name, icon: pendingSkill.icon, description: '', color: '#4a72a8', prompt: pendingSkill.prompt, group: '', rpcMethod: pendingSkill.rpcMethod }
    if (pendingSkill.prompt) {
      inputText.value = pendingSkill.prompt
      // 文档依赖型提示词（如"合同审查"）：无文档时提醒补充合同文本
      if (needsContractDocument(pendingSkill.prompt)) {
        ElMessage.info('审查合同需要先提供合同文本：点击 📎 上传合同文件，或直接粘贴合同内容后发送')
      }
    }
    nextTick(() => (document.querySelector('.chat-input textarea') as HTMLTextAreaElement)?.focus())
    return
  }
  // Fallback: pending prompt text (from dashboard quick question) — 自动发送
  const prompt = chatStore.consumePendingPrompt()
  if (prompt) {
    inputText.value = prompt
    // 文档依赖型提示词（如"合同审查"）：无文档时不自动发送，引导上传/粘贴
    if (needsContractDocument(prompt)) {
      ElMessage.info('审查合同需要先提供合同文本：点击 📎 上传合同文件，或直接粘贴合同内容后发送')
      nextTick(() => (document.querySelector('.chat-input textarea') as HTMLTextAreaElement)?.focus())
      return
    }
    // Auto-send for quick question flow (user already clicked "提问" on dashboard)
    nextTick(() => {
      if (inputText.value.trim() && !chatStore.loading) {
        sendMessage()
      }
    })
  }
  // 预填但不自动发送（专家召唤等场景：用户确认/补充后再发）
  const prefill = chatStore.consumePendingPrefill()
  if (prefill) inputText.value = prefill

  // 进入会话时定位到最新消息
  nextTick(() => { if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight })

  // Load backend hermes-agent skills
  skillStore.fetchBackendSkills()
})

// 流式输出期间跟随滚动（用户向上翻阅历史时暂停，滚回底部附近自动恢复）
watch(chatStore.messages, () => { scrollToBottom() }, { deep: true })

function formatTime(date: Date) { return new Date(date).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
</script>

<style scoped>
/* ═══════ Card container ═══════ */
.chat-panel {
  display: flex; flex-direction: column; height: 100%;
  margin: 16px 20px 20px;
  border-radius: var(--radius-xl);
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

/* ═══════ AG-UI Run Progress & Steps ═══════ */
.run-progress-wrap {
  margin: 10px 16px 0;
  background: linear-gradient(135deg, rgba(42,63,106,0.05), rgba(178,34,34,0.03));
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  overflow: hidden;
}
.run-progress-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 14px; cursor: pointer; user-select: none;
  transition: background .2s;
}
.run-progress-row:hover { background: rgba(42,63,106,0.05); }
.rp-left { display:flex; align-items:center; gap:8px; }
.rp-title { font-size: 13px; color: var(--legal-navy); font-weight: 500; }
.rp-right { display:flex; align-items:center; gap:4px; }

.run-step-list {
  padding: 4px 14px 12px;
  border-top: 1px dashed var(--el-border-color-lighter);
  display: flex; flex-direction: column; gap: 6px;
  max-height: 260px; overflow-y: auto;
}
.run-step-item {
  display: flex; gap: 8px; align-items: flex-start;
  padding: 6px 8px; border-radius: 6px;
  background: rgba(255,255,255,0.45);
}
.run-step-item.st-running { background: rgba(64,158,255,0.08); }
.run-step-item.st-ok { opacity: 0.9; }
.run-step-item.st-failed { background: rgba(245,108,108,0.08); }
.rs-indicator { flex-shrink:0; width: 18px; display:flex; align-items:center; padding-top:1px; }
.rs-skipped-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--el-border-color);
  margin-left: 3px;
}
.rs-body { flex: 1; min-width: 0; }
.rs-title-row {
  display: flex; align-items: center; gap: 6px;
  font-size: 12.5px;
}
.rs-kind-tag {
  font-size: 11px; padding: 1px 6px; border-radius: 4px;
  background: var(--legal-navy); color: white;
  font-weight: 500;
}
.run-step-item.kind-think .rs-kind-tag { background: #b58900; }
.run-step-item.kind-tool .rs-kind-tag { background: #2d7d4e; }
.run-step-item.kind-final .rs-kind-tag { background: #8b5cf6; }
.rs-title { color: var(--legal-text); flex:1; min-width:0; overflow:hidden; text-overflow: ellipsis; white-space: nowrap; }
.rs-idx { color: var(--legal-muted); font-size: 11px; flex-shrink:0; }
.rs-desc { font-size: 11.5px; color: var(--legal-muted); margin-top:2px; }
.rs-tool-preview {
  margin-top: 4px; padding: 4px 8px; font-size: 11.5px;
  background: rgba(45,125,78,0.08); color: #2d4e37;
  border-radius: 4px; border: 1px dashed rgba(45,125,78,0.2);
  font-family: var(--font-mono);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.rs-duration { font-size: 11px; color: var(--legal-muted); margin-top: 2px; }

/* Transitions */
.run-progress-enter-active, .run-progress-leave-active { transition: all .25s ease; }
.run-progress-enter-from, .run-progress-leave-to { opacity: 0; transform: translateY(-6px); max-height: 0; }
.step-list-enter-active, .step-list-leave-active { transition: all .22s ease; overflow: hidden; }
.step-list-enter-from, .step-list-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.step-list-enter-active, .step-list-leave-active { max-height: 400px; }

.spin { animation: spin 0.9s linear infinite; display: inline-flex; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.rotated { transform: rotate(90deg); transition: transform .2s; }

.messages {
  flex: 1; overflow-y: auto; padding: 20px 20px 12px; scroll-behavior: smooth;
}

/* ═══════ Welcome ═══════ */
.welcome { text-align: center; padding: 30px 20px 10px; }
.welcome-icon { font-size: 34px; margin-bottom: 6px; }
.welcome h2 { margin: 0 0 4px; color: var(--legal-navy); font-size: 18px; font-family: var(--font-heading); }
.welcome-desc { color: var(--legal-text-secondary); margin-bottom: 20px; font-size: 13px; }
.welcome-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; max-width: 440px; margin: 0 auto; }
.wg-item {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 10px 6px; border-radius: var(--radius-sm);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer; transition: all var(--transition-fast);
}
.wg-item:hover { border-color: var(--legal-gold); background: var(--legal-gold-bg); }
.wg-icon { font-size: 20px; }
.wg-label { font-size: 12px; font-weight: var(--weight-medium); color: var(--legal-navy); }

/* ═══════ Messages ═══════ */
.msg-row { display: flex; gap: 10px; margin-bottom: 20px; }
.msg-row.user { flex-direction: row-reverse; }
.msg-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; flex-shrink: 0; margin-top: 2px;
}
.msg-row.assistant .msg-avatar { background: var(--el-color-primary-light-9); border: 1px solid var(--el-color-primary-light-7); }
.msg-row.user .msg-avatar { background: var(--legal-gold-bg); border: 1px solid var(--legal-gold-lighter); }
.msg-body { max-width: 78%; min-width: 0; }
.msg-row.user .msg-body { display: flex; flex-direction: column; align-items: flex-end; }
.msg-name { font-size: 12px; color: var(--legal-text-muted); margin-bottom: 3px; }
.msg-role { color: var(--legal-gold-dark); font-size: 11px; }
.msg-ctx-line {
  font-size: 10.5px; color: var(--legal-text-muted);
  margin-top: 3px; opacity: 0.75; user-select: none;
}
.msg-bubble {
  padding: 10px 14px; border-radius: var(--radius-md);
  line-height: 1.7; font-size: 14px; word-break: break-word;
}
/* ── 失败/错误气泡：红色系边框 + 提示行 ── */
.msg-bubble-error {
  border: 1px solid var(--el-color-danger);
  background: color-mix(in srgb, var(--el-color-danger) 12%, transparent) !important;
}
.msg-error-hint {
  display: flex; align-items: center; gap: 4px;
  margin-top: 4px; font-size: 11px; color: var(--el-color-danger); opacity: .85;
}
.msg-bubble :deep(p) { margin: 0 0 6px; }
.msg-bubble :deep(p:last-child) { margin-bottom: 0; }
.msg-bubble :deep(ul), .msg-bubble :deep(ol) { padding-left: 20px; margin: 4px 0; }
.msg-bubble :deep(code) { background: var(--el-fill-color); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
.msg-bubble :deep(pre) { background: #1e1e2e; color: #cdd6f4; padding: 12px; border-radius: var(--radius-md); overflow-x: auto; font-size: 13px; }
.msg-bubble :deep(pre code) { background: transparent; padding: 0; color: inherit; }
.msg-bubble :deep(blockquote) { border-left: 3px solid var(--legal-gold); margin: 8px 0; padding: 4px 12px; color: var(--legal-text-secondary); background: #fafafc; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
.msg-bubble :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
.msg-bubble :deep(th), .msg-bubble :deep(td) { border: 1px solid var(--el-border-color); padding: 6px 10px; text-align: left; }
.msg-bubble :deep(th) { background: var(--el-fill-color); font-weight: 600; }
.msg-row.assistant .msg-bubble { background: var(--el-fill-color-lighter); border: 1px solid var(--el-border-color-lighter); color: var(--legal-text); }
.msg-row.user .msg-bubble { background: var(--legal-navy-bg); border: 1px solid var(--el-border-color-lighter); color: var(--legal-navy); }
.msg-citations { margin-top: 8px; }
.msg-cit-title {
  font-size: 11px; font-weight: 600; color: var(--legal-gold-dark); margin-bottom: 4px;
  display: flex; align-items: center; gap: 8px;
}
.msg-cit-copy {
  display: inline-flex; align-items: center; gap: 2px;
  border: none; background: transparent; cursor: pointer;
  font-size: 10.5px; color: var(--legal-text-muted);
  padding: 1px 6px; border-radius: 8px;
  transition: color var(--transition-fast), background var(--transition-fast);
}
.msg-cit-copy:hover { color: var(--legal-gold-dark); background: var(--legal-gold-bg); }
.msg-foot { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.msg-time { font-size: 11px; color: var(--legal-text-muted); }
.msg-tools { opacity: 0; transition: opacity 0.15s; display: inline-flex; gap: 2px; }
.msg-row:hover .msg-tools { opacity: 1; }
.msg-tool { color: var(--legal-text-muted); font-size: 12px; padding: 2px; }
.msg-tool:hover { color: var(--legal-navy); }
.typing { display: flex; gap: 4px; padding: 12px 16px; background: var(--el-fill-color-lighter); border-radius: var(--radius-md); border: 1px solid var(--el-border-color-lighter); }
.td { width: 8px; height: 8px; border-radius: 50%; background: var(--legal-text-muted); animation: bounce 1.4s infinite ease-in-out; }
.td:nth-child(2) { animation-delay: 0.2s; }
.td:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 80%, 100% { transform: translateY(0); } 40% { transform: translateY(-8px); } }

/* ═══════ File preview panel ═══════ */
.preview-panel {
  border-top: 1px solid var(--el-border-color-extra-light);
  background: var(--legal-bg-card);
  max-height: 40vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.pp-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 16px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  flex-shrink: 0;
}
.pp-name {
  font-size: 12px; font-weight: 500; color: var(--legal-navy);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;
}
.pp-actions { display: flex; gap: 2px; flex-shrink: 0; }
.pp-body { flex: 1; overflow-y: auto; padding: 12px 16px; }
.pp-img { max-width: 100%; max-height: 30vh; object-fit: contain; border-radius: var(--radius-sm); display: block; margin: 0 auto; }
.pp-textarea {
  width: 100%; min-height: 120px; border: 1px solid var(--el-border-color);
  border-radius: var(--radius-sm); padding: 10px; font-size: 13px; line-height: 1.6;
  resize: vertical; outline: none; background: var(--legal-bg-card); color: var(--legal-text);
  font-family: var(--font-ui);
}
.pp-textarea:focus { border-color: var(--legal-navy); }
.pp-markdown { font-size: 13px; line-height: 1.7; }
.pp-markdown :deep(p) { margin: 0 0 6px; }
.pp-markdown :deep(h1), .pp-markdown :deep(h2), .pp-markdown :deep(h3) { font-size: 15px; margin: 0 0 6px; color: var(--legal-navy); }
.pp-markdown :deep(code) { background: var(--el-fill-color); padding: 1px 4px; border-radius: 3px; font-size: 12px; }
.pp-markdown :deep(pre) { background: #1e1e2e; color: #cdd6f4; padding: 10px; border-radius: var(--radius-sm); overflow-x: auto; font-size: 12px; }
.pp-placeholder { text-align: center; padding: 20px 0; color: var(--legal-text-muted); }
.pp-placeholder p { margin: 6px 0 0; font-size: 13px; }
.pp-size { font-size: 11px; opacity: 0.6; }
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.15s ease; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; max-height: 0; }

/* ═══════ Input area (seamless with card) ═══════ */
.input-card {
  margin: 0 16px 12px;
  padding: 10px 12px 6px;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  transition: border-color var(--transition-fast), background var(--transition-fast);
}
/* 聚焦时整卡高亮（输入框自身无边框，边框语义上收到卡片） */
.input-card:focus-within {
  border-color: var(--legal-navy);
  background: var(--legal-bg-card);
}

/* ── Composer：输入框 + 发送按钮同行 ── */
.composer-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
.composer-send {
  flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  width: 40px; height: 34px; margin-bottom: 3px;
  border: none; border-radius: 10px;
  background: var(--legal-navy); cursor: pointer;
  color: #fff; font-size: 17px;
  transition: all var(--transition-fast); padding: 0;
}
.composer-send:hover { background: var(--legal-navy-light); }
.composer-send:disabled { opacity: 0.3; cursor: not-allowed; background: var(--legal-navy); }

/* ── Active pills row ── */
.pills-line { display: flex; gap: 4px; margin-bottom: 8px; flex-wrap: wrap; }

/* ── Bottom toolbar ── */
.pill {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 11px; padding: 1px 8px; border-radius: 10px; height: 20px;
  white-space: nowrap; max-width: 160px; overflow: hidden; text-overflow: ellipsis;
}
.pill-skill { background: rgba(212,168,67,0.12); color: var(--legal-gold-dark); }
.pill-expert { background: var(--legal-navy-bg); color: var(--legal-navy); }
.pill-case { background: var(--el-fill-color-light); color: var(--legal-text-secondary); }
.pill-file { background: var(--el-fill-color-lighter); color: var(--legal-text-secondary); }
.pill-icon { margin-right: 2px; }
.pill-x { cursor: pointer; opacity: 0.5; flex-shrink: 0; }
.pill-x:hover { opacity: 1; }
.pill-save { cursor: pointer; opacity: 0.4; flex-shrink: 0; margin-right: 1px; }
.pill-save:hover { opacity: 1; color: var(--legal-navy); }
.pf-dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 2px; }

/* ── Textarea ── */
.chat-input { flex: 1; }
.chat-input :deep(.el-input__wrapper) {
  border-radius: 10px;
  background: var(--el-fill-color-lighter);
  box-shadow: none;
  border: 1px solid var(--el-border-color);
  padding: 6px 12px;
}
.chat-input :deep(.el-input__wrapper):hover { border-color: var(--legal-navy); box-shadow: none; }
.chat-input :deep(.el-input__wrapper.is-focus) { border-color: var(--legal-navy); box-shadow: 0 0 0 1px var(--legal-navy) inset; background: var(--legal-bg-card); }
.chat-input :deep(textarea) { font-size: 14px; line-height: 1.5; min-height: 24px; }

/* ── Bottom toolbar ── */
.toolbar-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 6px;
}
.trl-left { display: flex; align-items: center; gap: 2px; }
.trl-right { display: flex; align-items: center; gap: 8px; }

.tb-btn {
  display: inline-flex; align-items: center; gap: 4px;
  height: 28px; padding: 0 10px; border: none; border-radius: var(--radius-sm);
  background: transparent; cursor: pointer;
  font-size: 12px; color: var(--legal-text-muted);
  transition: all var(--transition-fast); white-space: nowrap;
}
.tb-btn:hover { background: var(--el-fill-color-light); color: var(--legal-navy); }
.tb-btn.active { color: var(--legal-navy); background: var(--legal-navy-bg); }
.tb-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.tb-btn .el-icon { font-size: 15px; }

.trl-hint { font-size: 11px; color: var(--legal-text-muted); opacity: 0.45; }

/* ── 回到底部浮动按钮 ── */
.scroll-bottom-btn {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: 220px;
  z-index: 10;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  background: var(--legal-navy);
  color: #fff;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  transition: all var(--transition-fast);
}
.scroll-bottom-btn:hover {
  background: var(--legal-navy-light);
  transform: translateX(-50%) translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

/* ── Expert popover enhancements ── */
.ep-r-body { flex: 1; min-width: 0; }
.ep-r-desc {
  font-size: 11px;
  color: var(--legal-text-muted);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 1px;
}
.ep-r-usage {
  font-size: 10px;
  color: var(--legal-text-muted);
  background: var(--el-fill-color);
  padding: 0 6px;
  border-radius: 8px;
  line-height: 16px;
  flex-shrink: 0;
  margin-left: 4px;
}
.ep-r-star {
  flex-shrink: 0;
  cursor: pointer;
  opacity: 0.4;
  margin-right: 2px;
}
.ep-r-star:hover { opacity: 1; color: var(--legal-gold); }

/* ── Welcome expert recommendations ── */
.welcome-experts { margin-top: 14px; text-align: center; }
.welcome-expert-label { font-size: 11px; color: var(--legal-text-muted); margin-bottom: 6px; }
.welcome-expert-items { display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; }
.welcome-expert-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 12px;
  background: var(--legal-navy-bg);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer; font-size: 12px;
  transition: all var(--transition-fast);
}
.welcome-expert-chip:hover { border-color: var(--legal-navy); }

[data-theme="dark"] .welcome-expert-chip {
  background: var(--legal-navy-bg);
  border-color: var(--legal-border);
}
[data-theme="dark"] .welcome-expert-chip:hover {
  border-color: var(--legal-navy);
}

/* ── Welcome "view more" skills ── */
.welcome-more { margin-top: 10px; }
.welcome-more-text { font-size: 12px; color: var(--legal-text-muted); opacity: 0.7; }

/* ── Date separators ── */
.msg-date-sep { text-align: center; margin: 12px 0 16px; position: relative; }
.msg-date-sep::before {
  content: ''; position: absolute; left: 0; right: 0; top: 50%;
  height: 1px; background: var(--el-border-color-extra-light);
}
.msg-date-text {
  display: inline-block; font-size: 11px; color: var(--legal-text-muted);
  background: var(--legal-bg-card); padding: 0 10px; position: relative; z-index: 1;
}

/* ── Reasoning section ── */
.msg-reasoning {
  margin-top: 6px;
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.msg-reasoning-header {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 10px; font-size: 11px; color: var(--legal-text-muted);
  cursor: pointer; user-select: none;
  background: var(--el-fill-color-lighter);
}
.msg-reasoning-header:hover { color: var(--legal-navy); }
.msg-reasoning-body {
  padding: 8px 12px; font-size: 13px; line-height: 1.6;
  color: var(--legal-text-secondary);
  border-top: 1px solid var(--el-border-color-extra-light);
  max-height: 300px; overflow-y: auto;
}
.msg-reasoning-body :deep(p) { margin: 0 0 6px; }


/* ── Typing abort button ── */
.typing-area { display: flex; align-items: center; gap: 8px; }
.abort-btn { font-size: 12px; color: var(--legal-text-muted); flex-shrink: 0; }
.abort-btn:hover { color: var(--legal-danger); }

/* ── Tool activity indicator ── */
.tool-activity-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--legal-text-secondary);
  background: var(--legal-navy-bg);
  border-radius: var(--radius-sm);
  max-width: fit-content;
}
.tool-activity-text { white-space: nowrap; }
.tool-spin { animation: tool-spin 1s linear infinite; color: var(--legal-navy); }
@keyframes tool-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* ── Quick replies ── */
.welcome-quick-replies { margin-top: 16px; }
.welcome-qr-label { font-size: 11px; color: var(--legal-text-muted); margin-bottom: 8px; }
.welcome-qr-grid { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.welcome-qr-item {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 6px 12px; border-radius: 16px;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer; font-size: 12px;
  transition: all var(--transition-fast);
}
.welcome-qr-item:hover { border-color: var(--legal-navy); background: var(--legal-navy-bg); }
.welcome-qr-text { color: var(--legal-text); }

/* ── Message editing ── */
.msg-edit-overlay {
  margin-top: 8px;
  padding: 8px;
  background: var(--el-fill-color);
  border-radius: var(--radius-sm);
  border: 1px solid var(--el-border-color);
}
.msg-edit-actions {
  display: flex; gap: 6px; justify-content: flex-end; margin-top: 6px;
}
[data-theme="dark"] .msg-edit-overlay {
  background: var(--legal-bg-card);
  border-color: var(--legal-border);
}
</style>
