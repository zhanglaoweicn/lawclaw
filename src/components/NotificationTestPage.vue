<script setup lang="ts">
/**
 * 通知系统本地测试页
 * ============================================================
 *  使用说明：
 *  1. 开发环境（Vite dev server）：自动降级为浏览器 Notification API
 *  2. Tauri 环境：调用 Rust 层通知插件
 *  3. 点击"请求权限"后才可以发送通知（浏览器 + Tauri 都需要首次授权）
 *
 *  测试场景：
 *    A. 即时通知（立即弹出）
 *    B. 短期定时通知（3s/5s/10s 后触发，验证调度准确性）
 *    C. 期限四档提醒模拟（用 ±X 秒代替 ±X 天，模拟真实流程）
 *    D. 取消通知验证
 *    E. 批量注册 + 列表查询
 * ============================================================
 */
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import {
  sendNotification,
  scheduleNotification,
  cancelNotification,
  listScheduledNotifications,
  scheduleDeadlineReminders,
  cancelDeadlineReminders,
  requestNotificationPermission,
  isNotificationGranted,
  type ScheduledNotification,
} from '../lib/notification'
import type { DeadlineType } from '../types/legal'

// ── UI 状态 ──
const permissionGranted = ref(false)
const loading = reactive({
  request: false,
  send: false,
  schedule: false,
  list: false,
  cancel: false,
})

const testLog = ref<string[]>([])
const scheduledList = ref<ScheduledNotification[]>([])

function log(msg: string, type: 'info' | 'success' | 'warn' | 'error' = 'info') {
  const ts = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  const prefix = { info: 'ℹ️', success: '✅', warn: '⚠️', error: '❌' }[type]
  testLog.value.unshift(`[${ts}] ${prefix} ${msg}`)
  if (testLog.value.length > 100) testLog.value.pop()
}

// ── 初始化 ──
onMounted(async () => {
  permissionGranted.value = await isNotificationGranted()
  log(permissionGranted.value
    ? '通知权限已授予，可直接发送通知'
    : '通知权限未授予，请先点击"请求通知权限"')
})

// ── 1. 请求权限 ──
async function handleRequestPermission() {
  loading.request = true
  try {
    const granted = await requestNotificationPermission()
    permissionGranted.value = granted
    if (granted) {
      log('权限授予成功', 'success')
      ElMessage.success('通知权限已启用')
    } else {
      log('权限被拒绝，请在系统设置中手动开启', 'error')
      ElMessage.error('权限被拒绝')
    }
  } catch (e) {
    log('权限请求异常: ' + (e as Error).message, 'error')
  } finally {
    loading.request = false
  }
}

// ── 2A. 即时通知测试 ──
async function testSendNow(level: 1 | 2 | 3) {
  loading.send = true
  const map = {
    1: { title: '🟡 低优先级通知', body: '这是一条低优先级测试通知，请确认能正常接收。' },
    2: { title: '🟠 中优先级：举证期限预警', body: '案件「张三诉李四买卖合同纠纷」的举证期限将于 3 日内到期，请及时准备证据材料。' },
    3: { title: '🔴 高优先级：明日截止！', body: '案件「王五建设工程施工合同纠纷」的一审判决上诉期（15日）将于明日（2026-08-14）截止！' },
  }[level]
  log(`发送即时通知：${map.title}`)
  try {
    await sendNotification(map.title, map.body)
    log('通知已发送（查看系统通知中心）', 'success')
  } catch (e) {
    log('发送失败: ' + (e as Error).message, 'error')
  } finally {
    loading.send = false
  }
}

// ── 2B. 短期定时通知 ──
const shortTestCases = [
  { label: '3 秒后通知', delay: 3 },
  { label: '5 秒后通知', delay: 5 },
  { label: '15 秒后通知', delay: 15 },
]

async function testScheduleShort(delaySec: number) {
  loading.schedule = true
  const id = `short-test-${Date.now()}`
  const fireAt = new Date(Date.now() + delaySec * 1000)
  const title = `⏰ ${delaySec}s 定时通知`
  const body = `若您在 ${delaySec} 秒后看到此通知，说明定时调度工作正常。触发时间：${fireAt.toLocaleTimeString('zh-CN', { hour12: false })}`
  log(`注册通知 [${id.slice(-6)}]：${delaySec} 秒后触发 @ ${fireAt.toLocaleTimeString('zh-CN', { hour12: false })}`)
  try {
    await scheduleNotification(id, fireAt, title, body)
    log('注册成功，等待触发...', 'success')

    // 注册浏览器降级下的前端验证
    setTimeout(() => {
      log(`⏱️ 已过 ${delaySec} 秒，若通知正常触发应已看到（如果没看到可能是浏览器/Tauri 通知权限问题）`, 'warn')
    }, (delaySec + 1) * 1000)
  } catch (e) {
    log('注册失败: ' + (e as Error).message, 'error')
  } finally {
    loading.schedule = false
  }
}

// ── 2C. 期限四档提醒模拟 ──
// 因为真实场景用"天"计算，这里把天替换成秒，便于短时间观察
const mockMatterId = 'mock-matter-001'
const mockDeadlineId = 'mock-dl-001'
const mockDeadlineDate = new Date(Date.now() + 15 * 1000)  // 模拟 15 秒后的"期限日"
const mockDeadlineLabel: Record<DeadlineType, string> = { 'appeal-judgment': '判决上诉期（15日）' } as any
const mockMatterTitle = '张三诉李四买卖合同纠纷 [模拟]'

function testDeadlineReminders() {
  // 用自定义配置：把天数替代为秒数偏移（+7s / +3s / +1s / +0s 相对于 now 反向计算）
  const now = Date.now()
  // 模拟期限日 = now + 15 秒
  // 四档分别在：now+8s（7日前→距到期7秒）、now+12s（3日前）、now+14s（1日前）、now+15s（当日）
  const offsets: { offsetSec: number; title: string; body: string }[] = [
    {
      offsetSec: 8,
      title: '🟡 距期限还剩 7 秒',
      body: `案件「${mockMatterTitle}」的判决上诉期将于 7 秒后到期（真实场景：距到期 7 日提醒）`,
    },
    {
      offsetSec: 12,
      title: '🟠 距期限还剩 3 秒',
      body: `案件「${mockMatterTitle}」的判决上诉期将于 3 秒后到期，请立即处理。`,
    },
    {
      offsetSec: 14,
      title: '🔴 距期限还剩 1 秒',
      body: `案件「${mockMatterTitle}」的判决上诉期 1 秒后截止！`,
    },
    {
      offsetSec: 15,
      title: '⏰ 期限已到',
      body: `案件「${mockMatterTitle}」的判决上诉期今日截止，请立即提交上诉状。`,
    },
  ]

  log('=== 期限四档提醒模拟启动 ===', 'success')
  log(`模拟期限日：${mockDeadlineDate.toLocaleTimeString('zh-CN', { hour12: false })}（15 秒后）`)
  log(`提醒顺序：${offsets.map(o => `${o.offsetSec}秒@${o.title.slice(0, 2)}`).join(' → ')}`)

  offsets.forEach(async (o, i) => {
    const id = `deadline-${mockMatterId}-${mockDeadlineId}-sim-${i}`
    const fireAt = new Date(now + o.offsetSec * 1000)
    await scheduleNotification(id, fireAt, o.title, o.body, mockMatterId)
    log(`  [档${i + 1}] 注册：${o.offsetSec}s → ${fireAt.toLocaleTimeString('zh-CN', { hour12: false })}`)
  })

  log('=== 全部四档已注册，请观察通知顺序 ===', 'success')
}

async function cancelMockDeadlineReminders() {
  loading.cancel = true
  for (let i = 0; i < 4; i++) {
    const id = `deadline-${mockMatterId}-${mockDeadlineId}-sim-${i}`
    await cancelNotification(id)
  }
  log('已取消全部模拟期限提醒', 'success')
  loading.cancel = false
}

// ── 2D. 取消通知验证 ──
const cancelTestId = ref('')
async function testCancelFlow() {
  // 注册 10 秒后的通知，3 秒后取消，验证没有触发
  const id = `cancel-test-${Date.now()}`
  const fireAt = new Date(Date.now() + 10 * 1000)
  cancelTestId.value = id

  log(`取消测试：注册通知 ${id.slice(-6)}（10 秒后触发）`)
  await scheduleNotification(
    id, fireAt,
    '❌ 这条通知不应出现',
    '如果您看到了这条通知，说明取消机制失效了。',
  )
  log('注册完成，3 秒后将取消它...')

  setTimeout(async () => {
    const canceled = true  // JS 层降级的 cancel 无返回值
    try {
      await cancelNotification(id)
    } catch {}
    log(`已请求取消 [${id.slice(-6)}]，请继续观察：10 秒后若未弹出通知则取消成功 ✅`, 'success')
    setTimeout(() => {
      log('取消观察窗口（12s）已结束，若未收到上面的通知说明取消机制正常', 'info')
    }, 12 * 1000)
  }, 3000)
}

// ── 2E. 列出已调度通知 ──
async function refreshScheduledList() {
  loading.list = true
  try {
    scheduledList.value = await listScheduledNotifications()
    log(`列出已调度通知：共 ${scheduledList.value.length} 条`, 'success')
  } catch (e) {
    log('列表获取失败: ' + (e as Error).message, 'error')
  } finally {
    loading.list = false
  }
}

function formatUnix(ts: number): string {
  return new Date(ts * 1000).toLocaleString('zh-CN', { hour12: false })
}

function daysFromNow(ts: number): string {
  const diff = ts - Math.floor(Date.now() / 1000)
  if (diff < 0) return `已过期 ${-diff}s`
  if (diff < 60) return `${diff} 秒后`
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟后`
  if (diff < 86400) return `${(diff / 3600).toFixed(1)} 小时后`
  return `${(diff / 86400).toFixed(1)} 天后`
}

// ── 测试 ElementPlus 原生通知（作为参照组） ──
function testElNotification(level: 1 | 2 | 3) {
  const map = {
    1: { type: 'info' as const, title: '🟡 ElNotification 参照', msg: '这是 ElementPlus 的页面内通知，不经过系统' },
    2: { type: 'warning' as const, title: '🟠 ElNotification 参照', msg: '用于和系统级通知做对比，不会在应用关闭时弹出' },
    3: { type: 'error' as const, title: '🔴 ElNotification 参照', msg: '如果系统级通知未弹出，这条应该会看到（验证页面正常运行）' },
  }[level]
  log(`ElNotification 参照组 (type=${map.type})：作为系统通知的对照`)
  ElNotification({
    type: map.type,
    title: map.title,
    message: map.msg,
    duration: 6000,
    position: 'bottom-right',
  })
}
</script>

<template>
  <div class="notif-test-page">
    <div class="page-header">
      <h2>🔔 通知系统本地测试台</h2>
      <div class="header-badge" :class="permissionGranted ? 'ok' : 'warn'">
        <span class="dot"></span>
        {{ permissionGranted ? '权限：已授予' : '权限：未授予' }}
      </div>
    </div>

    <!-- ========= 基础操作区 ========= -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>🛠️ 基础操作</span>
          <el-button type="primary" :loading="loading.request" @click="handleRequestPermission" :disabled="permissionGranted">
            ① 请求通知权限
          </el-button>
        </div>
      </template>
      <div class="step-note">
        <strong>第 1 步</strong>：先请求权限。Windows 首次会弹出系统授权对话框，点击"允许"。
        若之前拒绝过，需到 <code>设置 → 通知 → LawClaw</code> 手动开启。
      </div>
    </el-card>

    <!-- ========= 场景 A：即时通知 ========= -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>🅰️ 场景 A：即时通知（立即弹出）</span>
          <span class="step-tag">第 2 步</span>
        </div>
      </template>
      <div class="button-group">
        <el-button :loading="loading.send" @click="testSendNow(1)">
          🟡 低优先级测试
        </el-button>
        <el-button type="warning" :loading="loading.send" @click="testSendNow(2)">
          🟠 举证期限预警
        </el-button>
        <el-button type="danger" :loading="loading.send" @click="testSendNow(3)">
          🔴 明日截止（高优先级）
        </el-button>
      </div>
      <div class="button-group" style="margin-top:10px">
        <span class="sub-label">参照组（ElementPlus 页面内通知，用于对比）：</span>
        <el-button @click="testElNotification(1)">info</el-button>
        <el-button type="warning" @click="testElNotification(2)">warning</el-button>
        <el-button type="danger" @click="testElNotification(3)">error</el-button>
      </div>
      <div class="step-note muted">
        预期：系统通知中心（右下角）弹出气泡，带标题和正文。Windows 通知会保留在"操作中心"直到手动清除。
      </div>
    </el-card>

    <!-- ========= 场景 B：短期定时通知 ========= -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>🅱️ 场景 B：短期定时通知（验证调度准确性）</span>
          <span class="step-tag">第 3 步</span>
        </div>
      </template>
      <div class="button-group">
        <el-button :loading="loading.schedule" @click="testScheduleShort(3)">
          3 秒后弹出
        </el-button>
        <el-button type="primary" :loading="loading.schedule" @click="testScheduleShort(5)">
          5 秒后弹出 ⭐ 推荐
        </el-button>
        <el-button :loading="loading.schedule" @click="testScheduleShort(15)">
          15 秒后弹出
        </el-button>
      </div>
      <div class="step-note muted">
        预期：按钮点击 N 秒后通知准时弹出。误差 ≤ ±200ms 即视为正常。
        如果使用浏览器降级，关闭此标签页则通知不会弹出（setTimeout 随页面销毁）。
      </div>
    </el-card>

    <!-- ========= 场景 C：期限四档提醒模拟 ========= -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>🅲 场景 C：期限四档提醒模拟</span>
          <div class="right-actions">
            <el-button :loading="loading.cancel" type="danger" plain @click="cancelMockDeadlineReminders" size="small">
              取消本组
            </el-button>
          </div>
        </div>
      </template>
      <div class="mock-info">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="模拟案件">
            {{ mockMatterTitle }}
          </el-descriptions-item>
          <el-descriptions-item label="模拟期限日">
            约 15 秒后（对应真实场景的期限当日）
          </el-descriptions-item>
          <el-descriptions-item label="期限类型">
            判决上诉期 15 日
          </el-descriptions-item>
          <el-descriptions-item label="四档触发序列">
            <el-tag type="success" size="small" effect="plain">第 8 秒：7 日前提醒</el-tag> &nbsp;
            <el-tag type="warning" size="small" effect="plain">第 12 秒：3 日前提醒</el-tag> &nbsp;
            <el-tag type="danger" size="small" effect="plain">第 14 秒：1 日前提醒</el-tag> &nbsp;
            <el-tag type="danger" size="small">第 15 秒：期限当日</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <div class="button-group">
        <el-button type="primary" @click="testDeadlineReminders">
          ▶️ 启动四档模拟（推荐先点这个，观察完整序列）
        </el-button>
      </div>
      <div class="step-note muted">
        预期：从第 8 秒开始每隔数秒弹出一条通知，共 4 条，频率逐步加快。
      </div>
    </el-card>

    <!-- ========= 场景 D：取消通知验证 ========= -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <span>🅳 场景 D：取消通知验证</span>
      </template>
      <div class="button-group">
        <el-button type="warning" @click="testCancelFlow">
          注册 → 3 秒后取消 → 验证 10 秒时不弹出
        </el-button>
      </div>
      <div class="step-note muted">
        预期：10 秒后<strong class="bad">不应</strong>弹出"❌ 这条通知不应出现"。如果弹出，说明取消逻辑有 Bug。
      </div>
    </el-card>

    <!-- ========= 场景 E：调度列表查询 ========= -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>🅴 场景 E：待触发通知列表（仅 Tauri 有效）</span>
          <el-button plain :loading="loading.list" @click="refreshScheduledList">
            🔄 刷新列表
          </el-button>
        </div>
      </template>
      <el-empty v-if="scheduledList.length === 0" description="暂无已调度的通知（或非 Tauri 环境）" :image-size="80" />
      <el-table v-else :data="scheduledList" size="small" stripe>
        <el-table-column prop="id" label="ID" width="180" show-overflow-tooltip />
        <el-table-column label="触发时间" width="180">
          <template #default="{ row }">{{ formatUnix(row.fire_at_unix) }}</template>
        </el-table-column>
        <el-table-column label="倒计时" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.fire_at_unix * 1000 < Date.now() ? 'danger' : 'success'">
              {{ daysFromNow(row.fire_at_unix) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" show-overflow-tooltip />
        <el-table-column prop="matter_id" label="关联案件" width="140" show-overflow-tooltip />
      </el-table>
      <div class="step-note muted">
        浏览器降级环境（非 Tauri）此表始终为空 — setTimeout 句柄无法从外部枚举。
      </div>
    </el-card>

    <!-- ========= 日志区 ========= -->
    <el-card class="section-card log-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>📝 测试日志（最新 100 条）</span>
          <el-button text @click="testLog = []" size="small">清空</el-button>
        </div>
      </template>
      <div class="log-list">
        <div v-if="testLog.length === 0" class="empty-log">
          暂无日志，点击上方按钮开始测试
        </div>
        <div v-for="(line, idx) in testLog" :key="idx" class="log-line">
          {{ line }}
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.notif-test-page {
  padding: 20px 24px 40px;
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: visible;  /* 外层 view-slot--internal-scroll 实际是 viewHasInternalScroll=true，
                         但 notification-test 页面较短，先统一交给外层滚动以避免双滚；
                         与 dashboard/skills 同级页面策略一致 */
  height: auto;
  min-height: 100%;

  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    h2 { margin: 0; font-size: 20px; }
    .header-badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 12px; border-radius: 16px; font-size: 13px;
      &.ok { background: rgba(103, 194, 58, 0.1); color: var(--el-color-success); }
      &.warn { background: rgba(230, 162, 60, 0.1); color: var(--el-color-warning); }
      .dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: currentColor;
      }
    }
  }

  .section-card {
    border-radius: 8px;
    .card-header {
      display: flex; align-items: center; justify-content: space-between; gap: 8px;
      .right-actions { display: flex; gap: 8px; }
    }
    .step-tag {
      padding: 2px 10px; background: var(--legal-navy); color: #fff;
      border-radius: 12px; font-size: 12px;
    }
  }

  .button-group {
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
    .sub-label {
      font-size: 13px; color: var(--el-text-color-secondary); margin-right: 6px;
    }
  }

  .step-note {
    margin-top: 12px; padding: 8px 12px;
    background: var(--el-fill-color-lighter);
    border-left: 3px solid var(--legal-navy);
    border-radius: 0 4px 4px 0;
    font-size: 13px; color: var(--el-text-color-regular);
    &.muted { color: var(--el-text-color-secondary); background: var(--el-fill-color-light); border-left-color: var(--el-border-color); }
    strong.bad { color: var(--el-color-danger); }
  }

  .mock-info {
    margin-bottom: 12px;
  }

  .log-card {
    .log-list {
      max-height: 340px; overflow-y: auto;
      font-family: Consolas, 'Courier New', monospace;
      font-size: 12.5px; line-height: 1.7;
      background: #0d1117; color: #c9d1d9;
      border-radius: 6px; padding: 10px 14px;
    }
    .log-line { border-bottom: 1px dashed #21262d; }
    .log-line:last-child { border-bottom: none; }
    .empty-log {
      text-align: center; padding: 24px;
      color: var(--el-text-color-placeholder);
    }
  }
}
</style>
