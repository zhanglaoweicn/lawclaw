<template>
  <div class="setup-wizard">
    <div class="setup-card">
      <div class="setup-header">
        <div class="brand">
          <span class="brand-icon">&#x2696;</span>
          <h1>LawClaw <span class="zh">律爪</span></h1>
        </div>
        <p class="subtitle">AI 驱动的律师智能助理。请先完成以下配置。</p>
      </div>

      <el-steps :active="step" align-center class="setup-steps" :space="300">
        <el-step title="API 配置" :status="step > 0 ? 'success' : undefined" />
        <el-step title="律师信息" :status="step > 1 ? 'success' : undefined" />
        <el-step title="消息平台" :status="step > 2 ? 'success' : undefined" />
        <el-step title="完成" :status="step > 3 ? 'success' : undefined" />
      </el-steps>

      <!-- Step 0: API Key -->
      <div v-if="step === 0" class="step-content">
        <h3>配置大模型 API</h3>
        <p class="hint">填入你自己的 API Key（支持 OpenAI 兼容接口）。建议先点「测试连接」验证可用，再继续。</p>
        <el-form label-position="top">
          <el-form-item label="API 地址">
            <el-input v-model="form.baseUrl" placeholder="https://api.openai.com/v1" />
          </el-form-item>
          <el-form-item label="模型名称">
            <el-input v-model="form.model" placeholder="deepseek-flash" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="form.apiKey" type="password" show-password placeholder="sk-..." />
          </el-form-item>
          <div class="test-row">
            <el-button :loading="testing" @click="onTestConnection">
              <el-icon v-if="!testing" style="margin-right:4px"><Connection /></el-icon>
              测试连接
            </el-button>
            <span v-if="!engineReady" class="test-result waiting">引擎启动中…（首次启动约 10–30 秒，连上后再点测试）</span>
            <span v-else-if="testResult" :class="['test-result', testResult.ok ? 'ok' : 'bad']">
              {{ testResult.ok ? `✓ 连接成功（${testResult.model}，${testResult.latency_ms ?? '?'}ms）` : testResult.message }}
            </span>
          </div>
        </el-form>
      </div>

      <!-- Step 1: Practice Profile -->
      <div v-if="step === 1" class="step-content">
        <h3>律师信息</h3>
        <p class="hint">帮助 LawClaw 提供更贴合您业务场景的回答。</p>
        <el-form label-position="top">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="姓名">
                <el-input v-model="form.name" placeholder="您的名字" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="律所名称">
                <el-input v-model="form.firm" placeholder="律师事务所" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="职位">
                <el-select v-model="form.title" placeholder="选择职位" style="width:100%">
                  <el-option label="合伙人" value="合伙人" />
                  <el-option label="资深律师" value="资深律师" />
                  <el-option label="律师" value="律师" />
                  <el-option label="实习律师" value="实习律师" />
                  <el-option label="法务" value="法务" />
                  <el-option label="其他" value="其他" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="执业年限">
                <el-input-number v-model="form.years" :min="0" :max="50" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="业务领域（可多选）">
            <el-checkbox-group v-model="form.practiceAreas">
              <el-checkbox label="民商事诉讼" value="民商事诉讼" />
              <el-checkbox label="合同纠纷" value="合同纠纷" />
              <el-checkbox label="劳动人事" value="劳动人事" />
              <el-checkbox label="知识产权" value="知识产权" />
              <el-checkbox label="公司并购" value="公司并购" />
              <el-checkbox label="房地产与建设工程" value="房地产与建设工程" />
              <el-checkbox label="婚姻家事" value="婚姻家事" />
              <el-checkbox label="刑事辩护" value="刑事辩护" />
              <el-checkbox label="行政诉讼" value="行政诉讼" />
              <el-checkbox label="常年法律顾问" value="常年法律顾问" />
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="团队规模">
            <el-radio-group v-model="form.teamSize">
              <el-radio value="solo">个人执业</el-radio>
              <el-radio value="small">2-10人</el-radio>
              <el-radio value="medium">11-50人</el-radio>
              <el-radio value="large">50人以上</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 2: Messaging Platform -->
      <div v-if="step === 2" class="step-content">
        <h3>消息平台（可选）</h3>
        <p class="hint">配置后，LawClaw 可在飞书或企业微信中接收和回复消息，随时随地处理工作。</p>

        <el-divider content-position="left">飞书</el-divider>
        <el-form label-position="top">
          <el-form-item>
            <el-switch v-model="form.feishuEnabled" active-text="启用飞书机器人" />
          </el-form-item>
          <template v-if="form.feishuEnabled">
            <el-form-item label="App ID">
              <el-input v-model="form.feishuAppId" placeholder="飞书应用的 App ID" />
            </el-form-item>
            <el-form-item label="App Secret">
              <el-input v-model="form.feishuAppSecret" type="password" show-password placeholder="飞书应用的 App Secret" />
            </el-form-item>
          </template>
        </el-form>

        <el-divider content-position="left">企业微信</el-divider>
        <el-form label-position="top">
          <el-form-item>
            <el-switch v-model="form.wecomEnabled" active-text="启用企业微信机器人" />
          </el-form-item>
          <template v-if="form.wecomEnabled">
            <el-form-item label="企业 ID (Corp ID)">
              <el-input v-model="form.wecomCorpId" placeholder="ww..." />
            </el-form-item>
            <el-form-item label="Bot ID">
              <el-input v-model="form.wecomBotId" placeholder="机器人的 ID" />
            </el-form-item>
            <el-form-item label="Secret">
              <el-input v-model="form.wecomSecret" type="password" show-password placeholder="机器人密钥" />
            </el-form-item>
          </template>
        </el-form>
      </div>

      <!-- Step 3: Done -->
      <div v-if="step === 3" class="step-content done-step">
        <div class="done-icon">
          <span>&#x2696;</span>
        </div>
        <h3>配置完成</h3>
        <p class="done-sub">欢迎使用 LawClaw 律爪，您的 AI 律师助理。</p>
        <div class="summary">
          <div class="summary-item">
            <span class="summary-label">API</span>
            <span class="summary-val">{{ form.baseUrl }}</span>
          </div>
          <div class="summary-item" v-if="form.name">
            <span class="summary-label">律师</span>
            <span class="summary-val">{{ form.name }} &middot; {{ form.firm || '未填写' }}</span>
          </div>
          <div class="summary-item" v-if="form.practiceAreas.length">
            <span class="summary-label">领域</span>
            <span class="summary-val">{{ form.practiceAreas.join('、') }}</span>
          </div>
          <div class="summary-item" v-if="form.feishuEnabled || form.wecomEnabled">
            <span class="summary-label">消息</span>
            <span class="summary-val">
              {{ form.feishuEnabled ? '飞书 ' : '' }}{{ form.wecomEnabled ? '企业微信' : '' }}
            </span>
          </div>
        </div>
      </div>

      <div class="setup-actions">
        <el-button v-if="step > 0" @click="prevStep">上一步</el-button>
        <span v-else />
        <el-button v-if="step < 3" type="primary" @click="nextStep" :disabled="!canNext">
          {{ stepText }}
        </el-button>
        <el-button v-if="step === 3" type="primary" @click="finish" size="large">开始使用 LawClaw</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection } from '@element-plus/icons-vue'
import { useSetupStore } from '../stores/setup'
import { useChatStore } from '../stores/chat'
import { backend } from '../lib/backend'

const emit = defineEmits<{ done: [] }>()
const setupStore = useSetupStore()
// 引擎（捆绑 Python 后端）从进程启动到可连通常要 8–30 秒。把「连上没有」显式展示出来，
// 免得用户在启动过程中点「测试连接」被「后端引擎未启动」误导。
const chatStore = useChatStore()
const engineReady = computed(() => chatStore.connected)

const SECRET_PLACEHOLDER = '••••••'

const step = ref(0)

const form = reactive({
  baseUrl: setupStore.baseUrl || 'https://api.deepseek.com/v1',
  model: setupStore.model || 'deepseek-flash',
  apiKey: setupStore.apiKey || '',
  name: setupStore.profile?.name || '',
  firm: setupStore.profile?.firm || '',
  title: setupStore.profile?.title || '',
  years: setupStore.profile?.yearsOfPractice || 0,
  practiceAreas: setupStore.profile?.practiceAreas || [],
  teamSize: setupStore.profile?.teamSize || 'solo',
  feishuEnabled: setupStore.feishuConfig?.enabled || false,
  feishuAppId: setupStore.feishuConfig?.appId || '',
  feishuAppSecret: setupStore.feishuConfig?.appSecret ? SECRET_PLACEHOLDER : '',
  wecomEnabled: setupStore.wecomConfig?.enabled || false,
  wecomCorpId: setupStore.wecomConfig?.corpId || '',
  wecomBotId: setupStore.wecomConfig?.botId || '',
  wecomSecret: setupStore.wecomConfig?.secret ? SECRET_PLACEHOLDER : '',
})

const canNext = computed(() => {
  if (step.value === 0) return !!form.apiKey && !!form.baseUrl
  return true
})

// ── 测试连接（真实调用一次最小补全） ──
const testing = ref(false)
const testResult = ref<{ ok: boolean; model?: string; latency_ms?: number; message?: string } | null>(null)

async function onTestConnection() {
  if (!form.apiKey) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const r = await backend.testLlm(form.apiKey, form.baseUrl, form.model)
    testResult.value = r
    if (!r.ok && r.message) ElMessage.error(r.message)
  } catch (e: any) {
    const m = e?.message || '连接失败'
    const starting = m.includes('未连接') || m.includes('启动中')
    testResult.value = { ok: false, message: starting ? '引擎仍在启动中，请稍候再点一次「测试连接」' : m }
  } finally {
    testing.value = false
  }
}

const stepText = computed(() => {
  if (step.value === 0) return '下一步'
  if (step.value === 1) return '下一步'
  if (step.value === 2) return '跳过此步'
  return '下一步'
})

function resolveSecret(v: string, stored: string | undefined) {
  return v === SECRET_PLACEHOLDER ? (stored || '') : v
}

function nextStep() {
  if (step.value === 0) {
    setupStore.setApiKey(form.apiKey, form.baseUrl, form.model)
  }
  if (step.value === 1) {
    setupStore.setProfile({
      name: form.name,
      firm: form.firm,
      title: form.title,
      yearsOfPractice: form.years,
      practiceAreas: form.practiceAreas,
      teamSize: form.teamSize as any,
      jurisdiction: ['中国'],
      feishu: { enabled: form.feishuEnabled, appId: form.feishuAppId, appSecret: resolveSecret(form.feishuAppSecret, setupStore.feishuConfig?.appSecret) },
      wecom: { enabled: form.wecomEnabled, corpId: form.wecomCorpId, botId: form.wecomBotId, secret: resolveSecret(form.wecomSecret, setupStore.wecomConfig?.secret) },
    })
  }
  if (step.value === 2) {
    setupStore.setProfile({
      name: form.name,
      firm: form.firm,
      title: form.title,
      yearsOfPractice: form.years,
      practiceAreas: form.practiceAreas,
      teamSize: form.teamSize as any,
      jurisdiction: ['中国'],
      feishu: { enabled: form.feishuEnabled, appId: form.feishuAppId, appSecret: resolveSecret(form.feishuAppSecret, setupStore.feishuConfig?.appSecret) },
      wecom: { enabled: form.wecomEnabled, corpId: form.wecomCorpId, botId: form.wecomBotId, secret: resolveSecret(form.wecomSecret, setupStore.wecomConfig?.secret) },
    })
    // Also try to save to backend immediately so feishu/wecom config persists
    const feishuSecret = resolveSecret(form.feishuAppSecret, setupStore.feishuConfig?.appSecret)
    const wecomSecret = resolveSecret(form.wecomSecret, setupStore.wecomConfig?.secret)
    backend.call('setup_save', {
      api_key: form.apiKey,
      base_url: form.baseUrl,
      model: form.model,
      feishu_app_id: form.feishuAppId,
      feishu_app_secret: feishuSecret,
      wecom_corp_id: form.wecomCorpId,
      wecom_bot_id: form.wecomBotId,
      wecom_secret: wecomSecret,
    }).catch((e: any) => console.warn('后端保存失败:', e))
  }
  step.value++
}

function prevStep() {
  step.value--
}

async function finish() {
  const feishuSecret = form.feishuAppSecret === SECRET_PLACEHOLDER
    ? (setupStore.feishuConfig?.appSecret || '')
    : form.feishuAppSecret
  const wecomSecret = form.wecomSecret === SECRET_PLACEHOLDER
    ? (setupStore.wecomConfig?.secret || '')
    : form.wecomSecret

  setupStore.complete()
  try {
    await backend.call('setup_save', {
      api_key: form.apiKey,
      base_url: form.baseUrl,
      model: form.model,
      feishu_app_id: form.feishuAppId,
      feishu_app_secret: feishuSecret,
      wecom_corp_id: form.wecomCorpId,
      wecom_bot_id: form.wecomBotId,
      wecom_secret: wecomSecret,
      // P0-3: 同时传律师画像，后端会写入 USER.md 让 Memory 系统加载
      profile: {
        name: form.name,
        firm: form.firm,
        title: form.title,
        yearsOfPractice: form.years,
        practiceAreas: form.practiceAreas,
        teamSize: form.teamSize,
      },
    })
  } catch (e) {
    console.warn('后端保存失败，仅保存到本地:', e)
  }
  emit('done')
}
</script>

<style scoped>
.setup-wizard {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--setup-bg-gradient, linear-gradient(135deg, #f2f3f7 0%, #e8eaf0 100%));
  overflow: auto;
}

.setup-card {
  width: 640px;
  max-height: 92vh;
  overflow-y: auto;
  background: var(--legal-bg-card);
  border-radius: var(--radius-xl);
  padding: 40px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--el-border-color-lighter);
}

.setup-header {
  text-align: center;
  margin-bottom: 32px;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 8px;
}

.brand-icon {
  font-size: 32px;
}

.setup-header h1 {
  font-size: 28px;
  margin: 0;
  color: var(--legal-navy);
  font-family: var(--font-heading);
}

.setup-header .zh {
  font-weight: 400;
  color: var(--legal-gold);
}

.subtitle {
  color: var(--legal-text-secondary);
  font-size: 14px;
  margin: 0;
}

.setup-steps {
  margin-bottom: 32px;
}

.step-content {
  min-height: 300px;
}

.step-content h3 {
  margin: 0 0 8px;
  font-size: 18px;
  font-family: var(--font-heading);
  color: var(--legal-navy);
}

.hint {
  color: var(--legal-text-secondary);
  font-size: 13px;
  margin: 0 0 20px;
}

/* ── 测试连接行 ── */
.test-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: -6px;
}
.test-result {
  font-size: 12px;
  line-height: 1.5;
}
.test-result.ok { color: var(--el-color-success); }
.test-result.bad { color: var(--el-color-danger); }
.test-result.waiting { color: var(--el-text-color-secondary); }

.setup-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-light);
}

.done-step {
  text-align: center;
  padding: 32px 0;
}

.done-icon {
  font-size: 48px;
  color: var(--legal-gold);
  margin-bottom: 8px;
}

.done-step h3 {
  margin: 12px 0 8px;
  font-size: 22px;
}

.done-sub {
  color: var(--legal-text-secondary);
  font-size: 14px;
  margin: 0 0 24px;
}

.summary {
  text-align: left;
  padding: 16px 20px;
  background: var(--el-fill-color);
  border-radius: var(--radius-md);
  font-size: 13px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.summary-item:last-child {
  border-bottom: none;
}

.summary-label {
  color: var(--legal-text-muted);
  font-weight: 500;
}

.summary-val {
  color: var(--legal-text);
  font-weight: 600;
  text-align: right;
}
</style>
