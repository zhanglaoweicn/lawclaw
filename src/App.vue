<template>
  <!-- 顶层启动编排：Splash → SetupWizard → Main UI（仅当 phase==='main' 渲染主界面）
       主界面和 Splash 用 Transition 切换，SetupWizard 独占全屏 -->
  <Transition name="root-fade" mode="out-in">
    <!-- A. 启动 / 加载阶段：SplashScreen 独占全屏（idle / check-setup / loading / ready） -->
    <SplashScreen
      v-if="!showMainUi && bootstrap.state.phase !== 'setup-wizard'"
      key="splash"
      :state="bootstrap.state"
      :leaving="splashLeaving"
    />

    <!-- B. 首次使用：SetupWizard 独占全屏（用户填完配置 → 继续进入加载 → 主界面） -->
    <SetupWizard
      v-else-if="bootstrap.state.phase === 'setup-wizard'"
      key="wizard"
      @done="onSetupDone"
    />

    <!-- C. 主界面：只有 phase==='main' 才挂载 DOM，所有服务就绪后再出现 -->
    <el-container
      v-else
      key="main"
      class="app-container"
      :class="{ 'is-sidebar-collapsed': uiStore.sidebarCollapsed }"
    >
    <div class="app-body">
      <el-aside
        v-if="showSidebar"
        :width="asideW + 'px'"
        :style="{ '--sb-w': asideW + 'px' }"
        class="app-sidebar"
      >
        <div class="sidebar-inner">
          <NavSidebar
            :active-view="currentView === 'assistant' ? 'assistant' : currentView"
            :connected="chatStore.connected"
            :collapsed="uiStore.sidebarCollapsed"
            @navigate="onNavNavigate"
            @toggle-collapse="uiStore.toggleSidebar()"
          />
        </div>
      </el-aside>

      <el-container>
        <el-header class="app-header">
          <div class="header-left">
            <el-tooltip :content="uiStore.sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'" placement="bottom">
              <el-button text @click="uiStore.toggleSidebar()" class="header-btn" aria-label="切换侧边栏">
                <el-icon v-if="!uiStore.sidebarCollapsed"><Fold /></el-icon>
                <el-icon v-else><Expand /></el-icon>
              </el-button>
            </el-tooltip>

            <!-- Breadcrumb: show when chat has a linked matter -->
            <template v-if="currentView === 'assistant' && matterStore.activeMatter">
              <el-breadcrumb separator="›" class="header-breadcrumb">
                <el-breadcrumb-item>
                  <el-button text class="header-link-btn" @click="currentView = 'dashboard'">工作台</el-button>
                </el-breadcrumb-item>
                <el-breadcrumb-item>
                  <el-button text class="header-link-btn" @click="onShowMatters">{{ matterStore.activeMatter.title }}</el-button>
                </el-breadcrumb-item>
                <el-breadcrumb-item>
                  <el-dropdown @command="onSessionCommand" trigger="click" class="session-switcher">
                    <span class="header-title" style="cursor:pointer;display:inline-flex;align-items:center;gap:4px;">
                      {{ headerTitle }}
                      <el-icon><ArrowDown /></el-icon>
                    </span>
                    <template #dropdown>
                      <el-dropdown-menu class="session-dropdown-menu">
                        <el-dropdown-item
                          v-for="s in chatStore.sessions"
                          :key="s.id"
                          :command="s.id"
                          :class="{ 'is-active': s.id === chatStore.activeSessionId }"
                        >
                          <span class="session-dd-title">{{ s.title }}</span>
                          <span class="session-dd-meta">{{ s.messageCount }}轮</span>
                        </el-dropdown-item>
                        <el-dropdown-item divided command="new-session">
                          <el-icon><Plus /></el-icon> 新对话
                        </el-dropdown-item>
                        <el-dropdown-item command="manage-sessions">
                          <el-icon><Operation /></el-icon> 管理会话
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </el-breadcrumb-item>
              </el-breadcrumb>
            </template>

            <!-- Session switcher dropdown (no linked matter) -->
            <template v-else-if="currentView === 'assistant'">
              <el-dropdown @command="onSessionCommand" trigger="click" class="session-switcher">
                <span class="header-title" style="cursor:pointer;display:inline-flex;align-items:center;gap:4px;">
                  {{ headerTitle }}
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu class="session-dropdown-menu">
                    <el-dropdown-item
                      v-for="s in chatStore.sessions"
                      :key="s.id"
                      :command="s.id"
                      :class="{ 'is-active': s.id === chatStore.activeSessionId }"
                    >
                      <span class="session-dd-title">{{ s.title }}</span>
                      <span class="session-dd-meta">{{ s.messageCount }}轮</span>
                    </el-dropdown-item>
                    <el-dropdown-item divided command="new-session">
                      <el-icon><Plus /></el-icon> 新对话
                    </el-dropdown-item>
                    <el-dropdown-item command="manage-sessions">
                      <el-icon><Operation /></el-icon> 管理会话
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>

            <!-- 常显"新对话"按钮：原藏在会话下拉两层内，不易发现（用户反馈） -->
            <el-tooltip v-if="currentView === 'assistant'" content="开始新的对话（Ctrl+N）" placement="bottom">
              <el-button text class="header-link-btn header-newchat" @click="onSessionCommand('new-session')">
                <el-icon><Plus /></el-icon> 新对话
              </el-button>
            </el-tooltip>
            <span v-else-if="currentView === 'calendar'" class="header-title">日程</span>
            <span v-else-if="currentView === 'experts'" class="header-title">专家</span>
            <span v-else-if="currentView === 'skills'" class="header-title">技能</span>
            <span v-else-if="currentView === 'cases'" class="header-title">案件</span>
            <span v-else-if="currentView === 'files'" class="header-title">文件</span>
            <span v-else-if="currentView === 'settings'" class="header-title">配置</span>
            <span v-else class="header-title">LawClaw 律爪</span>
          </div>
          <div class="header-right">
            <el-button text class="header-btn" @click="currentView = 'dashboard'" aria-label="返回工作台">
              <el-icon><DataBoard /></el-icon>
              <span v-if="!uiStore.sidebarCollapsed">工作台</span>
            </el-button>
          </div>
        </el-header>

        <el-main class="app-main">
          <!-- 页面外层：统一滚动；内部含自滚动布局的页面（ChatPanel/FilePanel/CaseDetail）设置 internal-scroll 移除外层滚动 -->
          <Transition name="page-fade" mode="out-in">
            <div
              :key="viewKey"
              class="view-slot"
              :class="[
                viewHasInternalScroll ? 'view-slot--internal-scroll' : 'view-slot--page-scroll'
              ]"
            >
              <LawyerDashboard
                v-if="currentView === 'dashboard'"
                @show-matters="onShowMatters"
                @show-chat="onNewChat"
                @show-calendar="onShowCalendar"
                @quick-action="onQuickAction"
                @open-matter="onOpenMatter"
                @open-session="onOpenSession"
                @open-limitation-calc="showLimitationCalc = true"
                @quick-question="onQuickQuestion"
              />
              <CaseListView
                v-else-if="currentView === 'cases' && caseViewStore.subView === 'list'"
                @select-case="onOpenMatter"
                @new-chat="onNewChat"
              />
              <CaseDetailView
                v-else-if="currentView === 'cases' && caseViewStore.subView === 'detail'"
                :matter-id="caseViewStore.selectedMatterId"
                @back="caseViewStore.showCaseList()"
                @open-chat="onOpenSession"
              />
              <ChatPanel v-else-if="currentView === 'assistant'" :key="chatStore.activeSessionId || 'no-session'" />
              <FilePanel v-else-if="currentView === 'files'" />
              <CalendarPage v-else-if="currentView === 'calendar'" />
              <ExpertGroupPage v-else-if="currentView === 'experts'" @enter-chat="onEnterExpertsChat" />
              <SkillPage v-else-if="currentView === 'skills'" @enter-chat="onEnterSkillChat" />
              <div v-else-if="currentView === 'settings'" class="settings-view-wrapper">
                <SettingsPanelFull @close="currentView = 'dashboard'" />
              </div>
              <NotificationTestPage v-else-if="currentView === 'notification-test'" />
              <div v-else class="placeholder-view">
                <el-empty :description="'未实现页面：' + currentView" />
              </div>
            </div>
          </Transition>
        </el-main>
      </el-container>
    </div>


    <div class="app-footer">
        <span class="keyboard-hint" title="快捷键提示">Ctrl+K 搜索 · Ctrl+N 新对话 · Ctrl+, 设置 · Ctrl+\ 侧边栏</span>
        <span class="disclaimer">本分析仅供参考，不构成正式法律意见。</span>
        <div class="footer-links">
          <!-- 开发工具只在 dev 构建显示，不暴露给最终用户 -->
          <template v-if="isDevBuild">
            <span class="dev-link" @click="currentView = 'notification-test'" title="开发环境：通知系统测试页">
              🔔 通知测试
            </span>
          </template>
        </div>
      </div>
    </el-container>
  </Transition>

  <!-- ══════════════════════════════════════════════════════════
       全局弹层 / 对话框：必须在 <Transition> 外（Transition 只允许 1 个直接子元素）
       它们不参与 Splash / SetupWizard / Main 的根级过渡
       ══════════════════════════════════════════════════════════ -->
  <GlobalSearch :visible="showSearch" @close="showSearch = false" @navigate="onSearchNavigate" />

  <LimitationCalculator v-model:visible="showLimitationCalc" @add-to-calendar="onLimitationAddToCalendar" />

  <!-- Session Management Dialog -->
  <el-dialog v-model="showSessionManager" title="管理会话" width="500px">
    <div v-if="chatStore.sessions.length === 0" style="text-align:center;padding:20px;color:var(--legal-text-muted)">
      <p>暂无会话</p>
    </div>
    <div v-else class="session-list">
      <div v-for="s in chatStore.sessions" :key="s.id" class="session-mgr-row"
        :class="{ active: s.id === chatStore.activeSessionId }">
        <div class="session-mgr-info" @click="switchToSession(s.id)">
          <div class="session-mgr-title">
            <template v-if="renamingId === s.id">
              <el-input v-model="renameText" size="small"
                @keyup.enter="confirmRename(s.id)" @blur="confirmRename(s.id)" />
            </template>
            <span v-else>{{ s.title }}</span>
          </div>
          <div class="session-mgr-meta">{{ s.messageCount }}轮对话 · {{ timeAgo(s.updatedAt) }}</div>
        </div>
        <div class="session-mgr-ops">
          <el-button text size="small" @click="startRename(s)" aria-label="重命名">
            <el-icon><Edit /></el-icon>
          </el-button>
          <el-popconfirm title="确认删除此会话？" @confirm="deleteSession(s.id)">
            <template #reference>
              <el-button text size="small" type="danger" aria-label="删除会话">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { Fold, Expand, DataBoard, ArrowDown, Plus, Operation, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSetupStore } from './stores/setup'
import { useChatStore } from './stores/chat'
import { useMatterStore } from './stores/matter'
import { useCaseViewStore } from './stores/caseView'
import { useUiStore, SIDEBAR_W } from './stores/ui'
import SplashScreen from './components/SplashScreen.vue'
import SetupWizard from './components/SetupWizard.vue'
import NavSidebar from './components/NavSidebar.vue'
import LawyerDashboard from './components/LawyerDashboard.vue'
import ChatPanel from './components/ChatPanel.vue'
import FilePanel from './components/FilePanel.vue'
import SettingsPanelFull from './components/SettingsPanelFull.vue'
import NotificationTestPage from './components/NotificationTestPage.vue'
import CaseListView from './components/cases/CaseListView.vue'
import CaseDetailView from './components/cases/CaseDetailView.vue'
import CalendarPage from './components/CalendarPage.vue'
import ExpertGroupPage from './components/ExpertGroupPage.vue'
import SkillPage from './components/SkillPage.vue'
import GlobalSearch from './components/GlobalSearch.vue'
import LimitationCalculator from './components/LimitationCalculator.vue'
import { useAppBootstrap } from './composables/useAppBootstrap'
import type { QuickActionId, AppView } from './types/legal'

const setupStore = useSetupStore()
const chatStore = useChatStore()
const matterStore = useMatterStore()
const caseViewStore = useCaseViewStore()
const uiStore = useUiStore()
const bootstrap = useAppBootstrap()

const currentView = ref<AppView>('dashboard')

/** 开发工具（通知测试）只在 dev 构建可见 */
const isDevBuild = import.meta.env.DEV

const showSidebar = ref(true)
const showSessionManager = ref(false)
const showSearch = ref(false)
const showLimitationCalc = ref(false)
const renamingId = ref<string | null>(null)
const renameText = ref('')
const splashLeaving = ref(false)

/* 只有 phase==='main' 时挂载主界面 DOM（确保加载完才渲染，避免闪白） */
const showMainUi = computed(() => bootstrap.state.phase === 'main')

/* 监听 phase 变化：ready → 开始淡出 Splash；main → 重置 + 兜底解锁 index.html 微 Splash */
watch(
  () => bootstrap.state.phase,
  (p, prev) => {
    if (p === 'ready') {
      // 启动画面触发组件自身的 leaving 淡出类
      splashLeaving.value = true
    } else if (p === 'main') {
      splashLeaving.value = false
      // ══ Bridge 兜底：再次隐藏 #splash-micro（useAppBootstrap 已调用一次，这里防止时序竞态）
      //    下一帧再执行，确保 Vue 组件级过渡已经开始
      requestAnimationFrame(() => {
        try {
          const fn = (window as unknown as { __hideLawClawSplash?: () => void }).__hideLawClawSplash
          if (typeof fn === 'function') fn()
        } catch { /* bridge 不存在时静默 */ }
      })
    } else if (p === 'loading' && prev === 'setup-wizard') {
      // Wizard 完成 → 再次进入 loading，重置 leaving
      splashLeaving.value = false
    }
  }
)

onMounted(() => {
  // App 挂载后立即进入启动流程管线
  //   1) 配置未完整 → phase='setup-wizard' 显示 Wizard
  //   2) 配置已完整 → phase='loading' 加载服务 → phase='ready' → 'main'
  bootstrap.start()
})

// 侧边栏宽度：折叠时 64，展开时用户自定义（夹在 200~280，默认 232）
const asideW = computed(() => uiStore.effectiveSidebarPx())

// 注：Pinia setup store 中暴露的 ref 会被自动解包，访问不需要 .value
// 侧栏已恢复纯导航（MatterList 快捷列表移除——案件切换走案件页/Ctrl+K/顶栏面包屑）

// 哪些页面内部是自滚动布局（自己管理高度/分栏）：给这些页关闭外层 view-slot 滚动，
// 避免"外层 + 内层"双滚动条。其他页关闭自身高度/滚动，交给外层 view-slot 唯一滚动。
const viewHasInternalScroll = computed(() =>
  currentView.value === 'assistant' ||
  currentView.value === 'files' ||
  (currentView.value === 'cases' && caseViewStore.subView === 'detail') ||
  currentView.value === 'settings'
)

// ── 通知检查/调度：已在 bootstrap._runPhase3 内执行（避免与后端连接竞争资源），
//    这里不再重复调用。

// ── Global keyboard shortcuts ──
function handleKeydown(e: KeyboardEvent) {
  const mod = e.ctrlKey || e.metaKey

  // 开发环境：Ctrl+Shift+F10 直接跳过启动（调试用）
  if (mod && e.shiftKey && e.key === 'F10') {
    e.preventDefault()
    bootstrap.skipToMain()
    return
  }

  // Escape 不需要 Ctrl 修饰键，单独处理（UX-2：覆盖所有弹层）
  if (e.key === 'Escape' && !mod) {
    let closed = false
    if (showSearch.value) { showSearch.value = false; closed = true }
    if (showSessionManager.value) { showSessionManager.value = false; closed = true }
    if (showLimitationCalc.value) { showLimitationCalc.value = false; closed = true }
    if (closed) e.preventDefault()
    return
  }

  if (!mod) return

  switch (e.key.toLowerCase()) {
    case 'n':
      e.preventDefault()
      if (e.shiftKey) {
        // Ctrl+Shift+N: new matter — navigate to cases and show create dialog
        caseViewStore.showCaseList()
        caseViewStore.triggerNewCaseDialog()
        currentView.value = 'cases'
      } else {
        // Ctrl+N: new chat
        chatStore.newSession()
        matterStore.setActiveMatter(null)
        currentView.value = 'assistant'
      }
      break
    case 'k':
      // Ctrl+K: global search
      e.preventDefault()
      showSearch.value = true
      break
    case ',':
      // Ctrl+,: settings
      e.preventDefault()
      currentView.value = 'settings'
      break
    case '\\':
      // Ctrl+\: toggle sidebar
      e.preventDefault()
      uiStore.toggleSidebar()
      break
    case '0':
      // Ctrl+0: reset sidebar width (UX convenience)
      e.preventDefault()
      uiStore.resetSidebarWidth()
      break
  }
}

onMounted(() => document.addEventListener('keydown', handleKeydown))
onUnmounted(() => document.removeEventListener('keydown', handleKeydown))

// 视口过窄时自动折叠侧边栏（< 1100px），宽屏再展开
const mql = window.matchMedia('(max-width: 1099px)')
function onWidthChange(e: MediaQueryListEvent | MediaQueryList) {
  if (e.matches && !uiStore.sidebarCollapsed) uiStore.setSidebarCollapsed(true)
}
onWidthChange(mql)
mql.addEventListener?.('change', onWidthChange as (e: MediaQueryListEvent) => void)

// 外层 Transition key：currentView + caseViewStore.subView + activeSessionId
// 任何一个维度变化都强制重建 view-slot，避免 Transition 缓存导致切换空白
const viewKey = computed(() => {
  const parts: string[] = [currentView.value]
  if (currentView.value === 'cases') parts.push(caseViewStore.subView, caseViewStore.selectedMatterId || '')
  if (currentView.value === 'assistant') parts.push(chatStore.activeSessionId || '')
  parts.push(uiStore.sidebarCollapsed ? 'c' : 'w')  // 侧边栏折叠态变化时强制重建（重新计算子页宽）
  return parts.join('|')
})

const headerTitle = computed(() => {
  if (currentView.value === 'assistant' && chatStore.activeSession) return chatStore.activeSession.title
  if (currentView.value === 'cases') {
    if (caseViewStore.subView === 'detail' && caseViewStore.selectedMatter) return caseViewStore.selectedMatter.title
    return '案件管理'
  }
  return 'LawClaw 律爪'
})

function onSetupDone() {
  // 用户填完 SetupWizard（首次配置）→ 回到 bootstrap 继续加载服务 → 加载完自动进主界面
  void bootstrap.onSetupWizardDone()
}

function onNavNavigate(view: string) {
  if (view === 'assistant') {
    chatStore.newSession()
    matterStore.setActiveMatter(null)  // 确保不关联任何案件
    currentView.value = 'assistant'
  } else if (view === 'cases') {
    caseViewStore.showCaseList()
    currentView.value = 'cases'
  } else {
    currentView.value = view as AppView
  }
}

function onShowMatters() {
  // 导航到案件页（旧逻辑只展开侧栏快捷列表——该列表已移除，纯导航侧栏下需真正切视图）
  caseViewStore.showCaseList()
  currentView.value = 'cases'
  uiStore.setSidebarCollapsed(false)
}

function onEnterExpertsChat(sessionId: string) {
  currentView.value = 'assistant'
}

function onEnterSkillChat(sessionId: string) {
  currentView.value = 'assistant'
}

function onShowCalendar() {
  currentView.value = 'calendar'
}

function onOpenSession(id: string) {
  chatStore.switchSession(id)
  currentView.value = 'assistant'
}

function onOpenMatter(id: string) {
  matterStore.setActiveMatter(id)
  caseViewStore.showCaseDetail(id)
  currentView.value = 'cases'
}

const SKILL_BY_ACTION: Partial<Record<QuickActionId, { skillId: string; skillName: string; icon: string; prompt: string }>> = {
  'legal-research': { skillId: 'prc-legal-research-law-search', skillName: '法规检索', icon: '🔍', prompt: '请帮我检索以下法律法规：\n\n相关法条：' },
  'contract-review': { skillId: 'commercial-review', skillName: '合同审查', icon: '📋', prompt: '请帮我审查以下合同，重点分析风险条款：\n\n合同内容：' },
  'document-draft': { skillId: 'legal/document-draft', skillName: '文书起草', icon: '✍️', prompt: '请帮我起草一份以下文书的提纲：\n\n文书类型：\n关键事实：' },
  'fee-calc': { skillId: 'legal/fee-calculator', skillName: '诉讼费计算', icon: '💰', prompt: '请帮我计算以下诉讼费用：\n\n争议金额：\n案件类型：' },
}

function onNewChat() {
  chatStore.newSession()
  matterStore.setActiveMatter(null)
  currentView.value = 'assistant'
}

function onQuickAction(id: QuickActionId) {
  if (id === 'limitation-calc') {
    showLimitationCalc.value = true
    return
  }
  const action = SKILL_BY_ACTION[id]
  if (!action) return
  chatStore.newSession()
  matterStore.setActiveMatter(null)
  chatStore.setPendingSkill({ id: action.skillId, name: action.skillName, icon: action.icon, prompt: action.prompt })
  currentView.value = 'assistant'
}

function onLimitationAddToCalendar(date: string, title: string) {
  ElMessage.success(`诉讼时效提醒已创建：${title}（${date}）`)
}

function onQuickQuestion(text: string) {
  chatStore.newSession()
  matterStore.setActiveMatter(null)
  chatStore.setPendingPrompt(text)
  currentView.value = 'assistant'
}

function onSearchNavigate(view: string, params?: Record<string, string>) {
  showSearch.value = false
  if (view === 'cases') {
    if (params?.matterId) {
      matterStore.setActiveMatter(params.matterId)
      caseViewStore.showCaseDetail(params.matterId)
    } else {
      caseViewStore.showCaseList()
    }
    currentView.value = 'cases'
  } else if (view === 'assistant') {
    currentView.value = 'assistant'
  } else if (view === 'files') {
    currentView.value = 'files'
  }
}

function onSessionCommand(cmd: string) {
  if (cmd === 'new-session') {
    chatStore.newSession()
    currentView.value = 'assistant'
  } else if (cmd === 'manage-sessions') {
    showSessionManager.value = true
  } else {
    chatStore.switchSession(cmd)
    currentView.value = 'assistant'
  }
}

function switchToSession(id: string) {
  chatStore.switchSession(id)
  showSessionManager.value = false
}

function startRename(s: { id: string; title: string }) {
  renamingId.value = s.id
  renameText.value = s.title
  nextTick(() => {
    const input = document.querySelector('.session-mgr-title .el-input__inner') as HTMLInputElement
    input?.focus()
    input?.select()
  })
}

function confirmRename(id: string) {
  if (renamingId.value === id && renameText.value.trim()) {
    chatStore.renameSession(id, renameText.value.trim())
  }
  renamingId.value = null
  renameText.value = ''
}

function deleteSession(id: string) {
  chatStore.deleteSession(id)
  ElMessage.success('会话已删除')
}


function timeAgo(date: Date) {
  const diff = Date.now() - new Date(date).getTime()
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${Math.floor(diff / 86400000)}天前`
}

// 保持 showSidebar 与折叠态同步（当侧栏宽度已经被折叠/展开时，显式显示侧栏）
watch(
  () => uiStore.sidebarCollapsed,
  () => { showSidebar.value = true },
  { immediate: true }
)
</script>

<style>
@import './styles/legal-theme.css';

html, body, #app { margin:0; padding:0; height:100%; overflow:hidden; }
.app-container { height:100vh; display:flex; flex-direction:column; }

.app-body { flex:1; display:flex; overflow:hidden; min-height:0; }

.app-sidebar {
  background: var(--legal-bg-card);
  border-right: 1px solid var(--el-border-color-light);
  overflow:hidden;
  transition: width 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: width;
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;     /* 侧栏唯一滚动条：NavSidebar + MatterList 统一 */
  overflow-x: hidden;
  scrollbar-width: thin;
}

/* 自定义侧栏滚动条：更细 + 随主题变色（避免双滚时颜色突兀）*/
.sidebar-inner::-webkit-scrollbar { width: 5px; }
.sidebar-inner::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 5px;
  transition: background 0.15s;
}
.sidebar-inner:hover::-webkit-scrollbar-thumb { background: var(--legal-border); }
[data-theme="dark"] .sidebar-inner:hover::-webkit-scrollbar-thumb { background: #3f464e; }

.sidebar-divider {
  width: 100%;
  height: 1px;
  margin: 8px 0;
  border-top: 1px solid var(--el-border-color-extra-light);
  border-left: none;
}

.app-header {
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:0 12px !important;
  height:48px !important;
  background: var(--legal-bg-card);
  border-bottom: 1px solid var(--el-border-color-light);
  backdrop-filter: saturate(180%) blur(10px);
  -webkit-backdrop-filter: saturate(180%) blur(10px);
}

.header-left { display:flex; align-items:center; gap:6px; flex:1; min-width:0; }
.header-btn { font-size:13px; }

.header-newchat { color: var(--legal-text-secondary) !important; }
.header-newchat:hover { color: var(--legal-gold) !important; }
.header-title {
  font-weight: 600;
  font-size: 14px;
  font-family: var(--font-heading);
  color: var(--legal-navy);
}

.header-right { display:flex; align-items:center; gap:4px; }

.app-main { padding:0; overflow:hidden; background: var(--legal-bg); }

/* ===== 双滚动条修复：view-slot 根据子页类型二选一 ===== */
.view-slot--page-scroll {
  /* 普通子页：唯一外层滚动条 */
  height:100%;
  min-height:0;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
}
.view-slot--internal-scroll {
  /* 自滚动子页（ChatPanel / FilePanel / CaseDetail）：关闭外层滚动 */
  height:100%;
  min-height:0;
  overflow:hidden;
}

/* ── Page transition ── */
.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}

.placeholder-view { display:flex; align-items:center; justify-content:center; height:100%; }

/* SettingsPage 是 internal-scroll 自滚动布局：外层 wrapper 必须给满高，内部 .sv-body 才有 flex:1 的参考高度 */
.settings-view-wrapper {
  height: 100%;
  min-height: 0;
  overflow: hidden;
  display: flex;
}

.app-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 4px 20px;
  background: transparent;
  border-top: 1px solid var(--el-border-color-lighter);
  text-align:center;
  font-size:10px;
  line-height:1;
  min-height: 26px;
}

.disclaimer {
  color: var(--legal-text-muted);
  font-family: var(--font-heading);
  opacity: 0.6;
}

.keyboard-hint {
  color: var(--legal-text-muted);
  opacity: 0.4;
  font-size: 10px;
  letter-spacing: 0.3px;
}

.seed-link {
  color: var(--legal-text-muted);
  opacity: 0.3;
  font-size: 10px;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.seed-link:hover {
  opacity: 0.8;
  color: var(--legal-gold-dark);
}
.footer-links {
  display: inline-flex;
  gap: 16px;
  align-items: center;
}
.dev-link {
  color: var(--legal-navy);
  opacity: 0.6;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(var(--legal-navy-rgb, 27, 57, 109), 0.06);
  border: 1px solid rgba(var(--legal-navy-rgb, 27, 57, 109), 0.15);
  transition: all 0.2s;
}
.dev-link:hover {
  opacity: 1;
  background: rgba(var(--legal-navy-rgb, 27, 57, 109), 0.12);
}

/* ── Session switcher dropdown ── */
.session-switcher { cursor: pointer; }

/* ── Header breadcrumb ── */
.header-breadcrumb {
  display: flex;
  align-items: center;
  gap: 0;
  margin-left: 4px;
}

.header-breadcrumb .el-breadcrumb__inner {
  display: inline-flex;
  align-items: center;
}

.header-link-btn {
  font-size: 13px;
  color: var(--legal-text-secondary);
  padding: 0 2px;
  height: auto;
}

.header-link-btn:hover {
  color: var(--legal-navy);
}

.session-dropdown-menu .el-dropdown-menu__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
}

.session-dropdown-menu .el-dropdown-menu__item.is-active {
  background: var(--el-color-primary-light-9);
  color: var(--legal-navy);
  font-weight: 600;
}

.session-dd-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.session-dd-meta {
  font-size: 11px;
  color: var(--legal-text-muted);
  margin-left: 12px;
  flex-shrink: 0;
}

/* ── Session management dialog ── */
.session-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-mgr-row {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
}

.session-mgr-row:hover { background: var(--el-fill-color-light); }
.session-mgr-row.active { background: var(--el-color-primary-light-9); }

.session-mgr-info {
  flex: 1;
  min-width: 0;
}

.session-mgr-title {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-mgr-meta {
  font-size: 12px;
  color: var(--legal-text-muted);
  margin-top: 2px;
}

.session-mgr-ops {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
}

.session-mgr-row:hover .session-mgr-ops {
  opacity: 1;
}

/* ── 侧边栏折叠态视觉规则（图标模式）──── */
.is-sidebar-collapsed {
  /* 折叠态时：按钮 span 隐藏，图标居中，标题中文隐藏 */
}
.is-sidebar-collapsed .sidebar-divider { display: none; }

/* 折叠态 + > 1099px 时，隐藏页脚快捷键文字（为了紧凑） */
@media (max-width: 1099px) {
  .app-footer .keyboard-hint { display: none; }
}
@media (max-width: 768px) {
  .app-footer { gap: 8px; padding: 4px 12px; }
  .app-footer .seed-link { display:none; }
}

/* 减少 prefers-reduced-motion 下动画 */
@media (prefers-reduced-motion: reduce) {
  * {
    transition-duration: 0.001ms !important;
    animation-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }
}

/* =========================================================
   顶层启动编排过渡样式 (Splash / SetupWizard → Main UI)
   ========================================================= */
.root-fade-enter-active,
.root-fade-leave-active {
  transition: opacity 380ms cubic-bezier(0.4, 0, 0.2, 1),
              transform 380ms cubic-bezier(0.22, 1, 0.36, 1);
}
.root-fade-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(0.995);
}
.root-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.998);
}

/* SetupWizard 在 Splash → Wizard 阶段需要全屏展示，而不是内嵌进 app-container（因为 app-container 不渲染）。
   原 SetupWizard 的布局是 flex 居中，这里给它匹配 Splash 的背景色调，避免颜色跳变。 */
#app > .setup-wizard,
#app > div > .setup-wizard {
  min-height: 100vh;
  background: radial-gradient(1200px 700px at 20% 0%, #f7f8fb 0%, #e9ecf3 60%, #e5e8f0 100%);
}
[data-theme="dark"] #app > .setup-wizard,
[data-theme="dark"] #app > div > .setup-wizard {
  background: radial-gradient(1200px 800px at 15% -10%, #121a2b 0%, #0d1117 55%, #06090f 100%);
}
</style>
