import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PracticeProfile, FeishuConfig, WecomConfig } from '../types/legal'

const SETUP_KEY = 'lawclaw_setup'

interface SetupState {
  apiKey: string
  baseUrl: string
  model: string
  profile: PracticeProfile | null
  completed: boolean
}

function defaultProfile(): PracticeProfile {
  return {
    name: '', firm: '', title: '', practiceAreas: [],
    teamSize: 'solo', yearsOfPractice: 0, jurisdiction: ['中国'],
    feishu: { enabled: false, appId: '', appSecret: '' },
    wecom: { enabled: false, corpId: '', botId: '', secret: '' },
  }
}

function loadState(): SetupState {
  try {
    const raw = localStorage.getItem(SETUP_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return {
    apiKey: '',
    baseUrl: 'https://api.deepseek.com/v1',
    model: 'deepseek-flash',
    profile: null,
    completed: false,
  }
}

function saveState(s: SetupState) {
  localStorage.setItem(SETUP_KEY, JSON.stringify(s))
}

export const useSetupStore = defineStore('setup', () => {
  const state = ref<SetupState>(loadState())

  const isComplete = computed(() => state.value.completed && !!state.value.apiKey)
  const apiKey = computed(() => state.value.apiKey)
  const baseUrl = computed(() => state.value.baseUrl)
  const model = computed(() => state.value.model)
  const profile = computed(() => state.value.profile)
  const feishuConfig = computed(() => state.value.profile?.feishu || defaultProfile().feishu)
  const wecomConfig = computed(() => state.value.profile?.wecom || defaultProfile().wecom)

  function setApiKey(key: string, url: string, modelName: string) {
    state.value.apiKey = key
    state.value.baseUrl = url
    state.value.model = modelName
    saveState(state.value)
  }

  function setProfile(p: PracticeProfile) {
    state.value.profile = p
    saveState(state.value)
  }

  function setFeishuConfig(cfg: FeishuConfig) {
    if (!state.value.profile) state.value.profile = defaultProfile()
    state.value.profile.feishu = cfg
    saveState(state.value)
  }

  function setWecomConfig(cfg: WecomConfig) {
    if (!state.value.profile) state.value.profile = defaultProfile()
    state.value.profile.wecom = cfg
    saveState(state.value)
  }

  function complete() {
    state.value.completed = true
    saveState(state.value)
  }

  function reset() {
    state.value = {
      apiKey: '', baseUrl: 'https://api.deepseek.com/v1',
      model: 'deepseek-flash', profile: null, completed: false,
    }
    localStorage.removeItem(SETUP_KEY)
  }

  function getEnvVars(): Record<string, string> {
    return {
      OPENAI_API_KEY: state.value.apiKey,
      OPENAI_BASE_URL: state.value.baseUrl,
      LAWCLAW_MODEL: state.value.model,
    }
  }

  return {
    isComplete, apiKey, baseUrl, model, profile,
    feishuConfig, wecomConfig,
    setApiKey, setProfile, setFeishuConfig, setWecomConfig,
    complete, reset, getEnvVars,
  }
})
