<template>
  <div class="citation-card" :class="{ 'citation-deprecated': isDeprecated }">
    <div class="citation-header">
      <el-tag size="small" :type="isDeprecated ? 'danger' : 'primary'" class="law-tag">{{ citation.law }}</el-tag>
      <span class="article-num">{{ citation.article }}</span>
      <!-- 法条有效性验证状态 -->
      <el-tag v-if="isDeprecated" size="small" type="danger" effect="dark">❌ 已废止</el-tag>
      <el-tag v-else-if="verifyStatus === 'valid'" size="small" type="success" effect="dark">✅ 现行有效</el-tag>
      <el-tag v-else-if="verifyStatus === 'invalid'" size="small" type="danger" effect="dark">❌ 已失效</el-tag>
      <el-tag v-else-if="verifyStatus === 'loading'" size="small" type="info" effect="plain">验证中...</el-tag>
      <el-tag v-else-if="verifyStatus === 'not-found'" size="small" type="warning" effect="plain">⚠️ 未找到</el-tag>
      <el-tag v-if="citation.source" size="small" effect="plain" type="info">{{ citation.source }}</el-tag>
    </div>

    <!-- 已废止警告 banner（最显眼位置） -->
    <div v-if="isDeprecated" class="citation-deprecation-banner">
      <div class="deprecation-title">
        <el-icon size="14"><WarningFilled /></el-icon>
        <span>该法律已于 {{ citation.effectiveUntil }} 废止</span>
      </div>
      <div v-if="citation.replacedBy" class="deprecation-replace">
        替代法律：<strong>{{ citation.replacedBy }}</strong>
      </div>
      <div v-if="citation.deprecationNote" class="deprecation-note">{{ citation.deprecationNote }}</div>
      <div class="deprecation-action">
        请律师以替代法律的对应条款为准，引用前请核对条款编号映射。
      </div>
    </div>

    <div class="citation-body">{{ citation.content }}</div>
    <!-- 验证详情 -->
    <div v-if="verifyDetail" class="citation-verify-detail">
      <span v-if="verifyDetail.publish_date">发布: {{ verifyDetail.publish_date }}</span>
      <span v-if="verifyDetail.department"> | {{ verifyDetail.department }}</span>
      <span v-if="verifyDetail.status"> | 状态: {{ verifyDetail.status }}</span>
    </div>
    <div class="citation-actions">
      <el-button v-if="citation.url" text size="small" type="primary" @click="openUrl" class="citation-link">
        <el-icon><Link /></el-icon> 查看原文
      </el-button>
      <el-button v-if="officialUrlReady" text size="small" type="primary" @click="openOfficialDoc" class="citation-link">
        <el-icon><Link /></el-icon> 官方原文
      </el-button>
      <el-button text size="small" @click="copyCitation">
        <el-icon><CopyDocument /></el-icon> 复制
      </el-button>
      <el-button v-if="!isDeprecated && verifyStatus !== 'loading'" text size="small" @click="verifyCitation">
        <el-icon><Refresh /></el-icon> 重新验证
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Link, Refresh, WarningFilled, CopyDocument } from '@element-plus/icons-vue'
import type { Citation } from '../types/legal'
import { backend } from '../lib/backend'
import { copyText } from '../lib/clipboard'

const props = defineProps<{ citation: Citation }>()

const verifyStatus = ref<'idle' | 'loading' | 'valid' | 'invalid' | 'not-found'>('idle')
const verifyDetail = ref<{ publish_date?: string; department?: string; status?: string } | null>(null)
/** NPC 验证成功时携带的官方法规 ID（用于获取官方原文下载链接） */
const npcBbbs = ref<string | null>(null)
const officialUrlReady = computed(() => !!npcBbbs.value)

/** 已废止法律：优先使用 extract_citations 时本地标注的字段；fallback 到 verify 结果 */
const isDeprecated = computed(() => {
  if (props.citation.deprecated) return true
  return verifyStatus.value === 'invalid' && verifyDetail.value?.status === '已废止'
})

async function verifyCitation() {
  if (!props.citation.law) return
  verifyStatus.value = 'loading'
  try {
    const result = await backend.verifyCitation(props.citation.law, props.citation.article || '')
    npcBbbs.value = (result as { bbbs?: string }).bbbs || null
    if (result.deprecated || result.valid === false) {
      verifyStatus.value = 'invalid'
      verifyDetail.value = {
        publish_date: result.publish_date || result.effective_until,
        status: result.status || '已废止',
      }
    } else if (result.valid === true) {
      verifyStatus.value = 'valid'
      verifyDetail.value = {
        publish_date: result.publish_date,
        department: result.department,
        status: result.status,
      }
    } else {
      verifyStatus.value = 'not-found'
    }
  } catch {
    verifyStatus.value = 'not-found'
  }
}

function openUrl() {
  if (props.citation.url) {
    window.open(props.citation.url, '_blank')
  }
}

/** 官方原文：经 NPC 官方下载签名 URL 打开法规 DOCX/PDF（约 1 小时有效） */
async function openOfficialDoc() {
  if (!npcBbbs.value) return
  try {
    const { url } = await backend.npcDocxUrl(npcBbbs.value)
    if (url) window.open(url, '_blank')
    else ElMessage.warning('未获取到官方原文链接')
  } catch (e: unknown) {
    ElMessage.warning((e as Error)?.message?.slice(0, 60) || '获取官方原文失败')
  }
}

/** 复制引用文本（content 即抽取时的原文片段，可直接粘贴进文书/检索框） */
async function copyCitation() {
  const c = props.citation
  const text = c.content || `《${c.law}》${c.article}`
  ;(await copyText(text)) ? ElMessage.success('引用已复制') : ElMessage.warning('复制失败')
}

onMounted(() => {
  // 已废止法律本地已标注，无需调用元典 API
  if (props.citation.deprecated) return
  // 自动验证（仅对 AI 生成的引用）
  if (props.citation.source === 'AI生成' || !props.citation.source) {
    verifyCitation()
  }
})
</script>

<style scoped>
.citation-card {
  border: 1px solid var(--el-border-color);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  margin-top: 8px;
  background: var(--el-fill-color-lighter);
  font-size: 13px;
  transition: box-shadow var(--transition-fast);
}

.citation-card:hover {
  box-shadow: var(--shadow-sm);
}

/* 已废止法律卡片：红色边框 + 浅红背景 */
.citation-deprecated {
  border-color: rgba(245, 108, 108, 0.5);
  background: rgba(245, 108, 108, 0.04);
}

.citation-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.law-tag {
  flex-shrink: 0;
}

.article-num {
  font-weight: 600;
  color: var(--legal-navy);
  font-size: 13px;
  font-family: var(--font-heading);
}

/* 已废止警告 banner */
.citation-deprecation-banner {
  margin: 6px 0 8px;
  padding: 10px 12px;
  background: rgba(245, 108, 108, 0.08);
  border-left: 3px solid var(--el-color-danger);
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.6;
}

.deprecation-title {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--el-color-danger);
  font-weight: 600;
  margin-bottom: 4px;
}

.deprecation-replace {
  color: var(--legal-text);
  margin-bottom: 4px;
}
.deprecation-replace strong {
  color: var(--legal-navy);
  font-weight: 600;
}

.deprecation-note {
  color: var(--legal-text-secondary);
  font-size: 11px;
  margin-bottom: 4px;
}

.deprecation-action {
  color: var(--legal-warning);
  font-size: 11px;
  padding-top: 4px;
  border-top: 1px dashed rgba(245, 108, 108, 0.3);
}

.citation-body {
  color: var(--legal-text-secondary);
  line-height: 1.6;
  font-size: 13px;
}

.citation-verify-detail {
  margin-top: 4px;
  font-size: 11px;
  color: var(--legal-text-muted);
}

.citation-actions {
  margin-top: 6px;
  display: flex;
  gap: 4px;
}

.citation-link {
  margin-top: 0;
}
</style>
