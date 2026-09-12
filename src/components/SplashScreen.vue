<script setup lang="ts">
/**
 * SplashScreen — 启动画面
 *
 * 设计原则：
 *  - 专业律师风：深蓝 (#1a2744) + 金色 (#c9a84c) 点缀，对比度高、气质稳重
 *  - 科技感：几何线条网格背景 + 水平扫光 + 图标金色脉动，全部纯 CSS，零图片依赖
 *  - 轻量化：不引入图片/字体资源，首帧即可渲染，无额外加载负担
 *  - 响应式：480px 下字号、进度条宽度自适应
 *  - 无障碍：尊重 prefers-reduced-motion
 */
import { computed } from 'vue'
import type { BootstrapState } from '../composables/useAppBootstrap'

interface Props {
  state: BootstrapState
  /** 外层驱动：phase='ready' 之后开始淡出（true → 添加 .is-leaving 类） */
  leaving?: boolean
}
const props = withDefaults(defineProps<Props>(), { leaving: false })

const progressStyle = computed(() => ({
  width: `${Math.max(0, Math.min(100, props.state.progress))}%`,
}))

const percentText = computed(() =>
  String(Math.round(props.state.progress)).padStart(2, '0') + '%'
)

// 后端离线降级警告（非致命）
const showWarning = computed(
  () => props.state.phase === 'loading' && !!props.state.warning
)
</script>

<template>
  <div class="splash-screen" :class="{ 'is-leaving': leaving }" aria-busy="true" role="status">
    <!-- 背景：几何线条 + 径向光晕 -->
    <div class="splash-bg" aria-hidden="true">
      <div class="splash-bg__grid"></div>
      <div class="splash-bg__glow splash-bg__glow--tl"></div>
      <div class="splash-bg__glow splash-bg__glow--br"></div>
      <div class="splash-bg__vignette"></div>
    </div>

    <!-- 水平金色扫光：暗示 "扫描/加载" -->
    <div class="splash-scan" aria-hidden="true"></div>

    <!-- 中央品牌 + 进度区 -->
    <div class="splash-content">
      <!-- 品牌区：⚖ 图标 + LawClaw + 副标题 -->
      <div class="splash-brand">
        <div class="splash-brand__icon" aria-hidden="true">
          <svg viewBox="0 0 64 64" width="72" height="72" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- 金色外框圆（渐变笔触） -->
            <circle cx="32" cy="32" r="30" class="splash-icon__ring" />
            <!-- 内部天平（简化几何，律师风） -->
            <g class="splash-icon__scale" transform="translate(0, -1)">
              <!-- 立柱 -->
              <path d="M32 14 L32 50" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>
              <!-- 横梁 -->
              <path d="M18 22 L46 22" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>
              <!-- 左盘（三角形） -->
              <path d="M14 22 L22 22 L18 32 Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
              <!-- 右盘（三角形） -->
              <path d="M42 22 L50 22 L46 32 Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
              <!-- 底座 -->
              <path d="M22 50 L42 50" stroke="currentColor" stroke-width="2.8" stroke-linecap="round"/>
            </g>
          </svg>
          <!-- 金色光点脉动 -->
          <span class="splash-brand__pulse" aria-hidden="true"></span>
        </div>
        <div class="splash-brand__text">
          <h1 class="splash-brand__title">LawClaw<span class="splash-brand__dot" aria-hidden="true">·</span><span class="splash-brand__zh">律爪</span></h1>
          <p class="splash-brand__subtitle">AI 驱动的律师智能工作台</p>
        </div>
      </div>

      <!-- 进度条 + 百分比 -->
      <div class="splash-progress" aria-label="启动进度" role="progressbar"
        :aria-valuenow="Math.round(state.progress)" aria-valuemin="0" aria-valuemax="100">
        <div class="splash-progress__track">
          <div class="splash-progress__fill" :style="progressStyle"></div>
          <div class="splash-progress__shine" :style="{ left: `${Math.round(state.progress)}%` }" aria-hidden="true"></div>
        </div>
        <span class="splash-progress__percent">{{ percentText }}</span>
      </div>

      <!-- 状态文字 -->
      <p class="splash-status" :key="state.statusText">{{ state.statusText }}</p>

      <!-- 降级警告条（后端未启动） -->
      <Transition name="splash-warn">
        <div v-if="showWarning" class="splash-warning" role="alert">
          <span class="splash-warning__dot" aria-hidden="true"></span>
          <span class="splash-warning__text">{{ state.warning }}</span>
        </div>
      </Transition>
    </div>

    <!-- 底部版本号（低调不抢戏） -->
    <div class="splash-footer">
      <span class="splash-footer__ver">Version 0.1.0</span>
      <span class="splash-footer__sep" aria-hidden="true">·</span>
      <span class="splash-footer__copy">© LawClaw · 为中国律师打造</span>
    </div>
  </div>
</template>

<style scoped>
/* =========================================================
   Splash —— 配色：Navy (#0f1a2e) base + Gold (#c9a84c) accent
   亮色模式：浅色米灰 + 藏青文字；暗色模式：深海军 + 金色文字
   所有颜色使用 CSS 变量，与 legal-theme.css 中定义保持语义一致
   ========================================================= */

.splash-screen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  overflow: hidden;
  /* 默认亮色，暗色时由 [data-theme="dark"] 覆盖 */
  --s-bg-0: #e9ecf3;
  --s-bg-1: #f7f8fb;
  --s-accent: #c9a84c;
  --s-accent-soft: rgba(201, 168, 76, 0.28);
  --s-accent-glow: rgba(201, 168, 76, 0.5);
  --s-text-1: #1a2744;
  --s-text-2: #4c5a78;
  --s-text-muted: #8a96b1;
  --s-progress-track: rgba(26, 39, 68, 0.10);
  --s-warn-bg: rgba(201, 168, 76, 0.12);
  --s-warn-border: rgba(201, 168, 76, 0.32);
  --s-grid: rgba(26, 39, 68, 0.06);
  color: var(--s-text-1);
  background:
    radial-gradient(1200px 700px at 20% 0%, var(--s-bg-1) 0%, var(--s-bg-0) 60%, #e5e8f0 100%);
  opacity: 1;
  visibility: visible;
  transition: opacity 380ms cubic-bezier(0.4, 0, 0.2, 1),
              visibility 380ms step-end;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}
[data-theme="dark"] .splash-screen {
  --s-bg-0: #06090f;
  --s-bg-1: #0d1117;
  --s-accent: #e0b652;
  --s-accent-soft: rgba(224, 182, 82, 0.24);
  --s-accent-glow: rgba(224, 182, 82, 0.55);
  --s-text-1: #e8ecf5;
  --s-text-2: #a8b3cf;
  --s-text-muted: #5d6887;
  --s-progress-track: rgba(255, 255, 255, 0.07);
  --s-warn-bg: rgba(224, 182, 82, 0.10);
  --s-warn-border: rgba(224, 182, 82, 0.28);
  --s-grid: rgba(232, 236, 245, 0.05);
  background:
    radial-gradient(1200px 800px at 15% -10%, #121a2b 0%, var(--s-bg-1) 55%, var(--s-bg-0) 100%);
}

/* 离开时淡出 → 让主界面淡入 */
.splash-screen.is-leaving {
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 420ms cubic-bezier(0.4, 0, 0.2, 1),
              visibility 420ms step-end;
}

/* =========================================================
   背景层：几何网格 + 两个角落径向光晕 + 暗角
   ========================================================= */
.splash-bg { position: absolute; inset: 0; pointer-events: none; }
.splash-bg__grid {
  position: absolute; inset: -20%;
  background-image:
    linear-gradient(var(--s-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--s-grid) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse at center, #000 45%, transparent 85%);
  -webkit-mask-image: radial-gradient(ellipse at center, #000 45%, transparent 85%);
  opacity: 0.9;
  transform: perspective(900px) rotateX(56deg) translateY(-10%);
  transform-origin: 50% 30%;
  animation: splash-grid-drift 18s linear infinite;
}
@keyframes splash-grid-drift {
  from { background-position: 0 0, 0 0; }
  to   { background-position: 0 132px, 132px 0; }
}
.splash-bg__glow {
  position: absolute; width: 520px; height: 520px;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.65;
}
.splash-bg__glow--tl {
  top: -180px; left: -160px;
  background: radial-gradient(circle, var(--s-accent-soft) 0%, transparent 70%);
  animation: splash-glow-breathe 7s ease-in-out infinite alternate;
}
.splash-bg__glow--br {
  bottom: -200px; right: -180px;
  background: radial-gradient(circle, rgba(106, 144, 192, 0.22) 0%, transparent 70%);
  animation: splash-glow-breathe 9s ease-in-out -3s infinite alternate;
}
@keyframes splash-glow-breathe {
  from { opacity: 0.45; transform: scale(0.96); }
  to   { opacity: 0.80; transform: scale(1.06); }
}
.splash-bg__vignette {
  position: absolute; inset: 0;
  background: radial-gradient(ellipse at center, transparent 40%, rgba(0, 0, 0, 0.18) 100%);
}
[data-theme="dark"] .splash-bg__vignette {
  background: radial-gradient(ellipse at center, transparent 40%, rgba(0, 0, 0, 0.55) 100%);
}

/* 水平扫光（科技感） */
.splash-scan {
  position: absolute;
  left: -20%; right: -20%;
  top: 20%; height: 2px;
  background: linear-gradient(90deg,
    transparent 0%,
    var(--s-accent-soft) 35%,
    var(--s-accent) 50%,
    var(--s-accent-soft) 65%,
    transparent 100%);
  opacity: 0.8;
  filter: blur(1px);
  animation: splash-scan-line 6.2s cubic-bezier(0.65, 0, 0.35, 1) infinite;
}
@keyframes splash-scan-line {
  0%   { transform: translateY(-15vh); opacity: 0; }
  10%  { opacity: 0.8; }
  85%  { opacity: 0.8; }
  100% { transform: translateY(90vh); opacity: 0; }
}

/* =========================================================
   中央内容
   ========================================================= */
.splash-content {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center;
  justify-content: center;
  padding: 40px 28px 80px;
  box-sizing: border-box;
}

/* 品牌 */
.splash-brand {
  display: flex; flex-direction: column; align-items: center; gap: 18px;
  margin-bottom: 44px;
  animation: splash-brand-in 720ms cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes splash-brand-in {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
.splash-brand__icon {
  position: relative;
  color: var(--s-accent);
  width: 84px; height: 84px;
  display: flex; align-items: center; justify-content: center;
  filter: drop-shadow(0 4px 22px var(--s-accent-soft));
}
.splash-icon__ring {
  stroke: currentColor;
  stroke-width: 1.6;
  fill: none;
  stroke-dasharray: 260;
  stroke-dashoffset: 260;
  animation: splash-ring-draw 1100ms cubic-bezier(0.65, 0, 0.35, 1) 120ms forwards;
}
@keyframes splash-ring-draw {
  to { stroke-dashoffset: 0; }
}
.splash-icon__scale {
  opacity: 0;
  transform-origin: 50% 50%;
  transform: translateY(2px) scale(0.92);
  animation: splash-scale-in 620ms cubic-bezier(0.22, 1, 0.36, 1) 680ms forwards;
}
@keyframes splash-scale-in {
  to { opacity: 1; transform: translateY(0) scale(1); }
}
/* 图标右下金色脉动光点 */
.splash-brand__pulse {
  position: absolute;
  right: 10px; bottom: 10px;
  width: 9px; height: 9px; border-radius: 50%;
  background: var(--s-accent);
  box-shadow: 0 0 0 0 var(--s-accent-glow);
  animation: splash-pulse 2.1s ease-out infinite;
}
@keyframes splash-pulse {
  0%   { box-shadow: 0 0 0 0 var(--s-accent-glow); opacity: 0.95; }
  70%  { box-shadow: 0 0 0 14px rgba(201, 168, 76, 0); opacity: 0.95; }
  100% { box-shadow: 0 0 0 0 rgba(201, 168, 76, 0); opacity: 0; }
}

.splash-brand__text { text-align: center; }
.splash-brand__title {
  margin: 0; padding: 0;
  font-size: 34px; font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--s-text-1);
  line-height: 1.1;
}
.splash-brand__dot {
  color: var(--s-accent);
  margin: 0 2px;
  font-weight: 600;
}
.splash-brand__zh {
  font-weight: 600;
  color: var(--s-accent);
  margin-left: 2px;
}
.splash-brand__subtitle {
  margin: 8px 0 0; padding: 0;
  font-size: 14px;
  letter-spacing: 0.12em;
  color: var(--s-text-2);
}

/* 进度条 */
.splash-progress {
  width: 100%; max-width: 460px;
  display: flex; align-items: center; gap: 14px;
  margin-bottom: 16px;
}
.splash-progress__track {
  flex: 1; height: 5px;
  border-radius: 999px;
  background: var(--s-progress-track);
  overflow: hidden;
  position: relative;
  backdrop-filter: blur(2px);
}
.splash-progress__fill {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  background: linear-gradient(90deg,
    #a8882e 0%,
    var(--s-accent) 45%,
    var(--s-accent-glow) 85%,
    #e0c878 100%);
  border-radius: 999px;
  box-shadow: 0 0 14px var(--s-accent-soft);
  transition: width 180ms linear;   /* composable 层做平滑 + 组件兜底 180ms */
}
/* fill 头部位移高光 */
.splash-progress__shine {
  position: absolute;
  top: 0; bottom: 0;
  width: 60px; transform: translateX(-30px);
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.55) 50%,
    transparent 100%);
  mix-blend-mode: plus-lighter;
  pointer-events: none;
}
[data-theme="dark"] .splash-progress__shine {
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.22) 50%,
    transparent 100%);
}
.splash-progress__percent {
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--s-text-2);
  min-width: 36px; text-align: right;
}

/* 状态文字（每换一段文字做一次淡入） */
.splash-status {
  margin: 0;
  min-height: 22px;
  font-size: 13px;
  color: var(--s-text-2);
  letter-spacing: 0.04em;
  animation: splash-status-in 360ms cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes splash-status-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* 降级警告条 */
.splash-warning {
  margin-top: 20px;
  display: inline-flex; align-items: center; gap: 10px;
  padding: 9px 16px;
  border-radius: 10px;
  background: var(--s-warn-bg);
  border: 1px solid var(--s-warn-border);
  font-size: 12.5px;
  color: var(--s-text-2);
  max-width: 520px;
}
.splash-warning__dot {
  flex: 0 0 auto;
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--s-accent);
  box-shadow: 0 0 0 3px var(--s-accent-soft);
}
.splash-warning__text { line-height: 1.55; }
.splash-warn-enter-active, .splash-warn-leave-active {
  transition: opacity 260ms ease, transform 260ms cubic-bezier(0.22, 1, 0.36, 1);
}
.splash-warn-enter-from, .splash-warn-leave-to {
  opacity: 0; transform: translateY(-6px);
}

/* 底部版本号 */
.splash-footer {
  position: absolute;
  left: 0; right: 0; bottom: 22px;
  display: flex; justify-content: center; align-items: center; gap: 8px;
  font-size: 12px;
  color: var(--s-text-muted);
  letter-spacing: 0.02em;
}
.splash-footer__sep { opacity: 0.5; }

/* =========================================================
   响应式：480px 以下压缩
   ========================================================= */
@media (max-width: 480px) {
  .splash-brand { gap: 14px; margin-bottom: 36px; }
  .splash-brand__icon { width: 68px; height: 68px; }
  .splash-brand__icon svg { width: 58px; height: 58px; }
  .splash-brand__title { font-size: 26px; }
  .splash-brand__subtitle { font-size: 12.5px; letter-spacing: 0.08em; }
  .splash-progress { max-width: 100%; padding: 0 8px; }
  .splash-footer { font-size: 11px; bottom: 16px; }
}

/* =========================================================
   无障碍：prefers-reduced-motion → 全部动画禁用（仅保留关键过渡）
   ========================================================= */
@media (prefers-reduced-motion: reduce) {
  .splash-bg__grid,
  .splash-bg__glow--tl,
  .splash-bg__glow--br,
  .splash-scan,
  .splash-icon__ring,
  .splash-icon__scale,
  .splash-brand__pulse,
  .splash-brand {
    animation: none !important;
  }
  .splash-icon__ring { stroke-dashoffset: 0; }       /* 画好的圆环直接显示 */
  .splash-icon__scale { opacity: 1; transform: none; }
  .splash-progress__fill { transition: width 60ms linear; }
}
</style>
