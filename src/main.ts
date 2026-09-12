import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// Element Plus 原生深色主题 CSS 变量（50+ 组件 token 统一由 EP 维护）。
// 本项目通过在 <html data-theme="dark"> 时给 :root 赋值 --el-bg-color* / --el-text-color*，
// 再叠加下面这个文件提供的 200+ EP 原生 dark vars，从而让所有 el-* 组件无死角适配暗色。
import 'element-plus/theme-chalk/dark/css-vars.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'

// 首启检测：不预写任何 apiKey —— 让 useAppBootstrap 的 check-setup 阶段
// 正常进入 SetupWizard，由用户填写自己的 Key（否则向导成为死代码，
// 且 "demo-mode" 假 Key 会被透传给后端导致所有对话失败）。
// 历史遗留：老用户 localStorage 里可能存有 demo-mode，后端
// _make_agent 会把该占位值回退到 backend/.env 的默认配置。
const SETUP_KEY = 'lawclaw_setup'
try {
  const raw = localStorage.getItem(SETUP_KEY)
  if (raw && (JSON.parse(raw)?.apiKey === 'demo-mode')) {
    localStorage.removeItem(SETUP_KEY)
  }
} catch { /* 损坏的 JSON 视同未配置 */ }

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
