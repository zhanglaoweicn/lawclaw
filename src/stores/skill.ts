/**
 * 法律技能库
 *
 * 对话框中的⚡闪电图标仅调用本库中的法律技能。
 * 其他通用技能由 hermes-agent 原生技能系统处理。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LegalSkill } from '../types/legal'
import { backend } from '../lib/backend'

const USAGE_KEY = 'lawclaw_skill_usage'
const CUSTOM_SKILLS_KEY = 'lawclaw_custom_skills'

function loadUsage(): Record<string, number> {
  try { return JSON.parse(localStorage.getItem(USAGE_KEY) || '{}') } catch { return {} }
}

function saveUsage(u: Record<string, number>) {
  localStorage.setItem(USAGE_KEY, JSON.stringify(u))
}

function loadCustomSkills(): LegalSkill[] {
  try { return JSON.parse(localStorage.getItem(CUSTOM_SKILLS_KEY) || '[]') } catch { return [] }
}

function saveCustomSkills(s: LegalSkill[]) {
  localStorage.setItem(CUSTOM_SKILLS_KEY, JSON.stringify(s))
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

const builtInSkills: LegalSkill[] = [
  // ── 法规检索（RPC 技能，调用后端真实法律数据库）──
  {
    id: 'legal-search', name: '法条速查', icon: '📖', color: '#2a3f6a',
    description: '查询法律法规、司法解释、部门规章，快速找到适用条文',
    prompt: '',
    group: '法律检索',
    rpcMethod: 'legal_search',
    searchType: 'law',
  },
  {
    id: 'case-search', name: '案例速查', icon: '🔍', color: '#4a72a8',
    description: '检索最高法指导案例、典型案例、裁判要旨',
    prompt: '',
    group: '法律检索',
    rpcMethod: 'legal_search',
    searchType: 'case',
  },
  {
    id: 'qwal-search', name: '权威案例', icon: '⚖️', color: '#8b5cf6',
    description: '检索指导性案例、公报案例、参考案例与官方裁判要旨',
    prompt: '',
    group: '法律检索',
    rpcMethod: 'legal_search',
    searchType: 'authoritative',
  },
  {
    id: 'cite-case-search', name: '法条反查', icon: '🔗', color: '#b45309',
    description: '输入法条号，反查援引该条文的裁判文书（如：民法典 第917条）',
    prompt: '',
    group: '法律检索',
    rpcMethod: 'legal_search',
    searchType: 'case-by-law',
  },
  {
    id: 'legal-update', name: '法规动态', icon: '📰', color: '#5a6a8a',
    description: '查询法律法规的最新修订、生效和废止状态',
    prompt: '请帮我查询以下法规的最新状态：\n\n法规名称：',
    group: '法律检索',
  },

  // ── 合同审阅 ──
  {
    id: 'contract-scan', name: '合同风险扫描', icon: '📋', color: '#2d7d4e',
    description: '快速扫描合同文本，标记风险条款并给出修改建议',
    prompt: '请帮我审阅以下合同，标记所有对签约方不利的风险条款，并给出修改建议：\n\n合同内容：',
    group: '合同审阅',
  },
  {
    id: 'clause-compare', name: '条款对比审查', icon: '⚖️', color: '#3fb950',
    description: '审查违约责任、赔偿上限、解除条件等核心条款的公平性',
    prompt: '请分析合同中关于违约责任、赔偿上限、解除条件的条款是否公平合理：\n\n合同内容：',
    group: '合同审阅',
  },
  {
    id: 'nda-review', name: '保密协议审查', icon: '🔒', color: '#58a6ff',
    description: '快速审阅 NDA 的保密范围、期限、例外情形',
    prompt: '请审阅这份保密协议，重点看保密范围、保密期限、例外情形和违约责任的约定是否均衡：\n\n协议内容：',
    group: '合同审阅',
  },

  // ── 文书起草 ──
  {
    id: 'pleading-draft', name: '起诉状起草', icon: '📝', color: '#b8973e',
    description: '根据案件事实生成民事起诉状、答辩状等诉讼文书',
    prompt: '请帮我起草一份以下案件的诉讼文书：\n\n文书类型：\n关键事实：',
    group: '文书起草',
  },
  {
    id: 'legal-opinion', name: '法律意见书', icon: '✍️', color: '#d29922',
    description: '就特定法律问题出具专业法律意见书',
    prompt: '请就以下问题出具一份法律意见书：\n\n问题：',
    group: '文书起草',
  },
  {
    id: 'contract-draft', name: '合同起草', icon: '📄', color: '#4a72a8',
    description: '根据商业条件起草规范的合同文本',
    prompt: '请帮我起草一份以下合同：\n\n合同类型：\n商业条件：',
    group: '文书起草',
  },

  // ── 法律分析 ──
  {
    id: 'risk-assessment', name: '法律风险评估', icon: '🛡️', color: '#f85149',
    description: '对交易或项目的法律风险进行结构化评估',
    prompt: '请对以下事项进行法律风险评估，识别主要风险点并提供防范建议：\n\n事项描述：',
    group: '法律分析',
  },
  {
    id: 'dd-checklist', name: '尽调清单生成', icon: '🔬', color: '#3fb950',
    description: '生成法律尽职调查清单，覆盖公司、股权、IP、劳动等维度',
    prompt: '请生成一份A轮融资的法律尽职调查清单，涵盖公司架构、股权、知识产权、劳动人事、重大合同、诉讼等方面。',
    group: '法律分析',
  },
  {
    id: 'fee-calc', name: '诉讼费速算', icon: '🧮', color: '#b22222',
    description: '计算案件受理费、保全费、执行费等诉讼相关费用',
    prompt: '请帮我计算以下诉讼费用：\n\n争议金额：\n案件类型：',
    group: '法律分析',
  },

  // ── 投融资 ──
  {
    id: 'ts-scan', name: 'TS/SPA 条款审查', icon: '📋', color: '#8b5cf6',
    description: 'Term Sheet / 股权购买协议核心条款风险筛查',
    prompt: '请帮我审查以下投资协议中的关键条款，重点识别对投资人不利的风险点：\n\n协议内容：',
    group: '投融资',
  },
  {
    id: 'sha-draft', name: '股东协议起草', icon: '🏛️', color: '#4a72a8',
    description: '起草优先购买权、反稀释、拖售权等股东协议核心条款',
    prompt: '请帮我起草一份股东协议的核心条款，包括：优先购买权、共同出售权、反稀释条款、拖售权、优先清算权等。',
    group: '投融资',
  },
  {
    id: 'equity-incentive', name: '股权激励方案', icon: '🎯', color: '#d29922',
    description: '员工股权激励方案设计与合规分析',
    prompt: '请设计一份员工股权激励方案，包括期权池比例、授予条件、行权安排、退出机制，并分析相关税务和合规要点。',
    group: '投融资',
  },
  {
    id: 'val-analysis', name: '对赌协议分析', icon: '💰', color: '#f85149',
    description: '分析对赌协议法律效力及风险边界，结合最高法司法观点',
    prompt: '请分析对赌协议的法律效力及风险边界，结合最高法关于对赌协议的司法观点，给出条款设计建议。',
    group: '投融资',
  },
]

export const useSkillStore = defineStore('skill', () => {
  const customSkills = ref<LegalSkill[]>(loadCustomSkills())
  const backendSkills = ref<LegalSkill[]>([])
  const backendSkillsLoaded = ref(false)

  async function fetchBackendSkills() {
    if (backendSkillsLoaded.value) return
    try {
      const res: any = await backend.call('list_hermes_skills', {})
      if (res?.skills) {
        backendSkills.value = res.skills.map((s: any) => ({
          id: s.id,
          name: s.name,
          icon: s.icon || '⚙️',
          description: s.description || '',
          prompt: '',
          color: s.color || '#6b7280',
          group: s.group || '未分类',
          rpcMethod: undefined,
          isBackendSkill: true as const,
        }))
      }
    } catch {
      // Backend not available — use built-in skills only
    }
    backendSkillsLoaded.value = true
  }

  const usageCount = ref<Record<string, number>>(loadUsage())

  const skills = computed(() => [...backendSkills.value, ...builtInSkills, ...customSkills.value])

  const allGroups = computed(() => {
    const groups = new Set(builtInSkills.map(s => s.group))
    customSkills.value.forEach(s => groups.add(s.group))
    return Array.from(groups)
  })

  function getSkillsByGroup(): Record<string, LegalSkill[]> {
    const map: Record<string, LegalSkill[]> = {}
    const all = skills.value
    for (const s of all) {
      if (!map[s.group]) map[s.group] = []
      map[s.group].push(s)
    }
    return map
  }

  function findSkill(id: string): LegalSkill | undefined {
    return skills.value.find(s => s.id === id)
  }

  function recordUsage(id: string) {
    usageCount.value[id] = (usageCount.value[id] || 0) + 1
    saveUsage(usageCount.value)
  }

  function getUsageCount(id: string): number {
    return usageCount.value[id] || 0
  }

  const mostUsed = computed(() => {
    return [...skills.value]
      .filter(s => (usageCount.value[s.id] || 0) > 0)
      .sort((a, b) => (usageCount.value[b.id] || 0) - (usageCount.value[a.id] || 0))
      .slice(0, 3)
  })

  function recordRecent(id: string) {
    const recent: string[] = JSON.parse(localStorage.getItem('lawclaw_skill_recent') || '[]')
    const filtered = recent.filter(x => x !== id)
    filtered.unshift(id)
    localStorage.setItem('lawclaw_skill_recent', JSON.stringify(filtered.slice(0, 10)))
  }

  // ── Custom skills CRUD ──
  function addCustomSkill(skill: Omit<LegalSkill, 'id'>): LegalSkill {
    const newSkill: LegalSkill = { ...skill, id: generateId() }
    customSkills.value.push(newSkill)
    saveCustomSkills(customSkills.value)
    return newSkill
  }

  function removeCustomSkill(id: string) {
    customSkills.value = customSkills.value.filter(s => s.id !== id)
    saveCustomSkills(customSkills.value)
  }

  function updateCustomSkill(id: string, updates: Partial<LegalSkill>) {
    const idx = customSkills.value.findIndex(s => s.id === id)
    if (idx !== -1) {
      customSkills.value[idx] = { ...customSkills.value[idx], ...updates }
      saveCustomSkills(customSkills.value)
    }
  }

  return {
    skills, customSkills, backendSkills, usageCount, allGroups, backendSkillsLoaded,
    getSkillsByGroup, findSkill,
    recordUsage, getUsageCount, mostUsed, recordRecent,
    addCustomSkill, removeCustomSkill, updateCustomSkill,
    fetchBackendSkills,
  }
})
