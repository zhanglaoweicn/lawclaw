/**
 * useAppBootstrap — LawClaw 启动编排器
 *
 * 流程状态机：
 *   check-setup → [if !setupComplete] setup-wizard → loading → ready → main
 *                 [if setupComplete]  loading → ready → main
 *
 * 加载阶段（带权重，用于进度条）：
 *   P1 恢复本地存储 / 基础 Stores        5%  → 20%   (15%)
 *   P2 连接后端 WebSocket                20% → 55%   (35%，最长 2.5s，超时降级)
 *   P3 初始化会话 / 业务数据 / 通知       55% → 80%   (25%)
 *   P4 预加载资源 / 预热渲染              80% → 95%   (15%)
 *   P5 完成缓冲 / 显示 "准备就绪"        95% → 100%  (5% + 350ms)
 */

import { ref, reactive, readonly } from 'vue'
import { useSetupStore } from '../stores/setup'
import { useThemeStore } from '../stores/theme'
import { useUiStore } from '../stores/ui'
import { useChatStore } from '../stores/chat'
import { useMatterStore } from '../stores/matter'
import { useCaseViewStore } from '../stores/caseView'

export type BootstrapPhase =
  | 'idle'
  | 'check-setup'
  | 'setup-wizard'
  | 'loading'
  | 'ready'
  | 'main'

export interface BootstrapState {
  phase: BootstrapPhase
  progress: number        // 0..100，用于进度条
  statusText: string      // Splash 下方描述文字
  backendOnline: boolean | null  // true=已连 / false=离线降级 / null=未知
  warning?: string        // 非致命警告（如 "后端未启动，降级为本地模式"）
}

/* ── 全局单例 ── */
let _instance: ReturnType<typeof _createBootstrap> | null = null

export function useAppBootstrap() {
  if (!_instance) _instance = _createBootstrap()
  return _instance
}

/* ── 内部工厂 ── */
function _createBootstrap() {
  const state = reactive<BootstrapState>({
    phase: 'idle',
    progress: 0,
    statusText: '正在启动…',
    backendOnline: null,
  })

  // 平滑进度动画：使用 RAF 不跳变
  let _raf: number | null = null
  let _targetProgress = 0
  // ══ 全局兜底超时：任何阶段都不能 >15s 不进主界面，避免用户感知"卡死"
  //    进入 phase='main' 后清掉；倒计时结束强制 skipToMain()
  let _deadlineTimer: ReturnType<typeof setTimeout> | null = null
  function _resetDeadline(ms: number = 15000) {
    if (_deadlineTimer != null) { clearTimeout(_deadlineTimer); _deadlineTimer = null }
    _deadlineTimer = setTimeout(() => {
      if (state.phase !== 'main' && state.phase !== 'setup-wizard') {
        // setup-wizard 允许用户慢慢填，不强制跳；其余阶段超时视为阻塞，强制进主
        state.warning = state.warning ?? '启动超时，已跳过等待（部分服务可能未就绪）'
        skipToMain()
      }
    }, ms)
  }
  function _clearDeadline() {
    if (_deadlineTimer != null) { clearTimeout(_deadlineTimer); _deadlineTimer = null }
  }
  const _runSmoothProgress = () => {
    if (_raf != null) cancelAnimationFrame(_raf)
    const step = () => {
      const diff = _targetProgress - state.progress
      if (Math.abs(diff) < 0.3) {
        state.progress = _targetProgress
        _raf = null
        return
      }
      state.progress += diff * 0.18  // 指数缓动，视觉上更专业
      _raf = requestAnimationFrame(step)
    }
    _raf = requestAnimationFrame(step)
  }
  const _setTarget = (p: number, text?: string) => {
    _targetProgress = Math.max(0, Math.min(100, p))
    if (text != null) state.statusText = text
    _runSmoothProgress()
    // ══ Bridge：同步进度到 index.html 里的 #splash-micro（首帧微 Splash 零依赖可见）
    try {
      const fn = (window as unknown as { __lawclawSplashProgress?: (p: number, t?: string) => void }).__lawclawSplashProgress
      if (typeof fn === 'function') fn(_targetProgress, state.statusText)
    } catch { /* bridge 不存在时静默 */ }
  }

  // ══ Bridge：进入主界面（phase==='main'）时淡出 #splash-micro + 解锁 #app visibility
  //    必须在 ready → main 过渡后调用，否则 Vue 组件 SplashScreen 还没离开就把它盖掉了
  function _tryHideMicroSplash() {
    try {
      const fn = (window as unknown as { __hideLawClawSplash?: () => void }).__hideLawClawSplash
      if (typeof fn === 'function') fn()
    } catch { /* bridge 不存在时静默 */ }
  }

  /* 小工具：最小耗时保护（避免进度条闪跳太快 → 用户感知 "假"） */
  const _delay = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

  /* ── 入口：启动流程（可重入，用于 Wizard 完成后再次进入 loading） ── */
  async function start() {
    const setupStore = useSetupStore()
    state.warning = undefined
    state.backendOnline = null

    // 兜底计时器：从 start() 起 15s 内必须进 main，否则强制跳过
    _resetDeadline(15000)

    // Step 0: 检查配置完整性
    state.phase = 'check-setup'
    _setTarget(2, '检查用户配置…')
    await _delay(180)  // 给 Splash 品牌渐显预留一点时间

    if (!setupStore.isComplete) {
      // 交给外层显示 SetupWizard
      state.phase = 'setup-wizard'
      _setTarget(5, '等待配置完成…')
      _tryHideMicroSplash()  // ══ CRITICAL：解锁 #app visibility，让 SetupWizard 真正可见！
      // setup-wizard 阶段清掉兜底计时（用户填表多久都允许），等 done 回调再重建
      _clearDeadline()
      return
    }

    // 配置已完整 → 进入正式加载
    await _runLoadingPipeline()
  }

  /* ── Wizard 完成回调 → 继续进入加载阶段 ── */
  async function onSetupWizardDone() {
    _resetDeadline(15000)  // 重启兜底计时
    await _runLoadingPipeline()
  }

  /* ── 核心加载管线 ── */
  async function _runLoadingPipeline() {
    state.phase = 'loading'
    try {
      // P1: 基础 store 恢复（同步，加一个最小时延保证进度条可见）
      const p1Done = _runPhase1()
      await Promise.all([p1Done, _delay(260)])
      _setTarget(20, '本地数据已恢复')

      // P2: 后端 WS 连接（最长 2.5s，超时降级为本地模式，不阻塞主流程）
      const p2Done = _runPhase2()
      const p2Timer = _delay(2500).then(() => 'timeout' as const)
      const p2Res = await Promise.race([p2Done, p2Timer])
      if (p2Res === 'timeout') {
        state.backendOnline = false
        state.warning = '后端服务未启动（降级为本地模式，对话功能受限）'
        _setTarget(55, state.warning)
      } else {
        _setTarget(55, '后端服务已连接')
      }

      // P3: 业务数据 / 会话 / 通知调度
      await Promise.all([_runPhase3(), _delay(220)])
      _setTarget(80, '业务环境已就绪')

      // P4: 预加载（动态 import 一些重组件 / 预热 store）
      await Promise.all([_runPhase4(), _delay(180)])
      _setTarget(95, '正在进入工作台…')

      // P5: 准备就绪，短暂停留让用户看到 100%
      await _delay(260)
      _setTarget(100, '准备就绪')
      state.phase = 'ready'
      await _delay(380)  // 淡出过渡交给外层（380ms 内淡出 Splash + 淡入 Main）
      state.phase = 'main'
      _tryHideMicroSplash()  // ══ Bridge：解锁 #app 可见性 + 移除 index.html 微 Splash
      _clearDeadline()       // ══ 兜底计时器关闭
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      state.warning = state.warning ?? msg
      // 出错不挂死，降级进入主界面（用户还能改配置）
      state.phase = 'ready'
      state.statusText = '部分服务加载失败，已进入主界面'
      _setTarget(100)
      await _delay(380)
      state.phase = 'main'
      _tryHideMicroSplash()  // ══ Bridge：降级路径也必须解锁
      _clearDeadline()       // ══ 兜底计时器关闭
    }
  }

  /* ── P1: 本地 Store 恢复（同步即可，Pinia 内部懒加载） ── */
  async function _runPhase1() {
    // 预先读取这些 store，触发其初始化（恢复 localStorage / 计算默认值）
    useThemeStore()
    useUiStore()
    useMatterStore()
    useCaseViewStore()
    // chatStore 在 P2 连接，这里只 ensure 本地数据在
    const chat = useChatStore()
    chat.ensureFirstSession()
    state.progress = Math.min(state.progress, 8)  // 至少 8%
  }

  /* ── P2: 后端连接 ── */
  async function _runPhase2() {
    const chat = useChatStore()
    try {
      await chat.connectBackend()
      state.backendOnline = !!chat.connected
    } catch {
      state.backendOnline = false
    }
  }

  /* ── P3: 业务数据 + 通知调度 ── */
  async function _runPhase3() {
    try {
      const { useScheduleStore } = await import('../stores/schedule')
      const sched = useScheduleStore()
      // 检查通知权限但不等待，设置一下标记就够了
      void sched.checkNotificationStatus().catch(() => undefined)
      // 重新调度所有期限提醒（后台跑，不阻塞启动）
      void sched.rescheduleAllDeadlineReminders().catch(() => undefined)
    } catch {
      /* schedule 初始化失败不影响启动 */
    }
  }

  /* ── P4: 预加载（Webpack/Vite chunk 提前加载，避免首屏卡顿） ── */
  async function _runPhase4() {
    try {
      // 常用重组件：异步 prefetch，避免主界面切换时才加载
      await Promise.allSettled([
        import('../components/SkillPage.vue'),
        import('../components/ExpertGroupPage.vue'),
        import('../components/cases/CaseListView.vue'),
        import('../components/CalendarPage.vue'),
        import('../components/FilePanel.vue'),
      ])
    } catch {
      /* 预加载失败不阻塞 */
    }
  }

  /* ── 调试辅助：强制跳过（例如开发环境快捷键 Ctrl+Shift+F10） ── */
  function skipToMain() {
    state.phase = 'main'
    state.progress = 100
    state.statusText = ''
    _tryHideMicroSplash()  // ══ Bridge：调试跳过路径也要解锁 #app
    _clearDeadline()       // ══ 兜底计时器关闭（含兜底超时内部调用时自清除）
  }

  return {
    state: readonly(state) as Readonly<BootstrapState>,
    start,
    onSetupWizardDone,
    skipToMain,
  }
}
