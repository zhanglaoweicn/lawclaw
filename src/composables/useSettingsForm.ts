import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useSetupStore } from '../stores/setup'
import { backend } from '../lib/backend'

const SECRET_PLACEHOLDER = '••••••'

export function useSettingsForm() {
  const setupStore = useSetupStore()
  const activeTab = ref('model')

  const form = reactive({
    baseUrl: '', model: '', apiKey: '',
    name: '', firm: '', title: '', years: 0,
    practiceAreas: [] as string[], teamSize: 'solo' as string,
    feishuEnabled: false, feishuAppId: '', feishuAppSecret: '',
    wecomEnabled: false, wecomCorpId: '', wecomBotId: '', wecomSecret: '',
  })

  function loadFromStore() {
    form.baseUrl = setupStore.baseUrl || 'https://apihub.agnes-ai.com/v1'
    form.model = setupStore.model || 'agnes-2.0-flash'
    form.apiKey = setupStore.apiKey || ''
    form.name = setupStore.profile?.name || ''
    form.firm = setupStore.profile?.firm || ''
    form.title = setupStore.profile?.title || ''
    form.years = setupStore.profile?.yearsOfPractice || 0
    form.practiceAreas = setupStore.profile?.practiceAreas || []
    form.teamSize = setupStore.profile?.teamSize || 'solo'
    form.feishuEnabled = setupStore.feishuConfig?.enabled || false
    form.feishuAppId = setupStore.feishuConfig?.appId || ''
    form.feishuAppSecret = setupStore.feishuConfig?.appSecret ? SECRET_PLACEHOLDER : ''
    form.wecomEnabled = setupStore.wecomConfig?.enabled || false
    form.wecomCorpId = setupStore.wecomConfig?.corpId || ''
    form.wecomBotId = setupStore.wecomConfig?.botId || ''
    form.wecomSecret = setupStore.wecomConfig?.secret ? SECRET_PLACEHOLDER : ''
  }

  async function save() {
    const feishuSecret = form.feishuAppSecret === SECRET_PLACEHOLDER
      ? (setupStore.feishuConfig?.appSecret || '')
      : form.feishuAppSecret
    const wecomSecret = form.wecomSecret === SECRET_PLACEHOLDER
      ? (setupStore.wecomConfig?.secret || '')
      : form.wecomSecret

    setupStore.setApiKey(form.apiKey, form.baseUrl, form.model)
    setupStore.setProfile({
      name: form.name, firm: form.firm, title: form.title,
      yearsOfPractice: form.years, practiceAreas: form.practiceAreas,
      teamSize: form.teamSize as any, jurisdiction: ['中国'],
      feishu: { enabled: form.feishuEnabled, appId: form.feishuAppId, appSecret: feishuSecret },
      wecom: { enabled: form.wecomEnabled, corpId: form.wecomCorpId, botId: form.wecomBotId, secret: wecomSecret },
    })
    try {
      await backend.call('setup_save', {
        api_key: form.apiKey, base_url: form.baseUrl, model: form.model,
        feishu_app_id: form.feishuAppId, feishu_app_secret: feishuSecret,
        wecom_corp_id: form.wecomCorpId, wecom_bot_id: form.wecomBotId, wecom_secret: wecomSecret,
      })
    } catch (e) {
      console.warn('后端保存失败，仅保存到本地:', e)
      ElMessage.warning('后端保存失败，配置仅保存到本地')
      return // Don't show success if backend failed
    }
    // 成功提示由调用方（SettingsPanelFull.handleSave）统一发出，含后端连通状态，此处不重复 toast
  }

  /** validate baseUrl format */
  function validateBaseUrl(url: string): boolean {
    if (!url) return false
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      ElMessage.warning('API 地址需要以 http:// 或 https:// 开头')
      return false
    }
    return true
  }

  /** Test connection to backend */
  const testingConnection = ref(false)

  async function testConnection(): Promise<boolean> {
    if (!validateBaseUrl(form.baseUrl)) return false
    if (!form.apiKey) {
      ElMessage.warning('请先填写 API Key')
      return false
    }
    testingConnection.value = true
    try {
      // 真实调用一次最小补全（test_llm），能查出 Key 失效/欠费/限流/模型名错误
      const r = await backend.testLlm(form.apiKey, form.baseUrl, form.model)
      if (r.ok) {
        ElMessage.success(`连接成功！模型 ${r.model}，延迟 ${r.latency_ms ?? '?'}ms`)
        return true
      }
      ElMessage.error(r.message || '连接失败，请检查 API Key 与网络')
      return false
    } catch (e: any) {
      const msg = e?.message || '连接失败'
      if (msg.includes('not connected') || msg.includes('未连接')) {
        ElMessage.warning('LawClaw 后端引擎未启动，请先启动引擎')
      } else {
        ElMessage.error(`连接失败: ${msg}`)
      }
      return false
    } finally {
      testingConnection.value = false
    }
  }

  // Provider presets（Anthropic 官方 API 非 OpenAI 兼容，需经代理的用户请手填代理地址）
  const PROVIDER_PRESETS = [
    { label: 'Agnes AI (默认)', baseUrl: 'https://apihub.agnes-ai.com/v1', model: 'agnes-2.0-flash' },
    { label: 'OpenAI', baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o' },
    { label: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
    { label: '智谱 GLM', baseUrl: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-plus' },
    { label: '百度千帆', baseUrl: 'https://aip.baidubce.com/rpc/2.0/ai/custom/v1/wenxinworkshop/chat', model: 'ernie-4.0' },
    { label: '阿里百炼', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
    { label: '本地 Ollama', baseUrl: 'http://localhost:11434/v1', model: 'llama3.1' },
  ]

  function applyPreset(preset: typeof PROVIDER_PRESETS[0]) {
    form.baseUrl = preset.baseUrl
    form.model = preset.model
  }

  // MCP loading
  const mcpServers = ref<{ name: string; url: string; enabled: boolean }[]>([])
  const mcpLoading = ref(false)
  const mcpError = ref('')

  async function loadMcpServers() {
    mcpLoading.value = true
    mcpError.value = ''
    try {
      const res: any = await backend.call('list_mcp_servers', {})
      mcpServers.value = res?.servers || []
    } catch (e: any) {
      mcpError.value = e?.message || '无法加载数据源信息'
      mcpServers.value = []
    } finally {
      mcpLoading.value = false
    }
  }

  return {
    activeTab, form, mcpServers, mcpLoading, mcpError, testingConnection,
    loadFromStore, save, testConnection, loadMcpServers,
    validateBaseUrl, PROVIDER_PRESETS, applyPreset, SECRET_PLACEHOLDER,
  }
}
