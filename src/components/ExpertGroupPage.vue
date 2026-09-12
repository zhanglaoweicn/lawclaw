<template>
  <div class="expert-page">
    <div class="ep-header">
      <div>
        <h2 class="page-title">专家</h2>
        <p class="page-subtitle">按领域分类的专家团队，可单独召唤或整团召唤</p>
      </div>
    </div>

    <!-- Category tabs -->
    <div class="ep-categories">
      <div
        v-for="cat in categories" :key="cat.key"
        :class="['ep-cat-tab', { active: activeCategory === cat.key }]"
        @click="activeCategory = cat.key"
      >
        <span class="ep-cat-icon">{{ cat.icon }}</span>
        <div class="ep-cat-info">
          <span class="ep-cat-name">{{ cat.name }}</span>
          <span class="ep-cat-desc">{{ cat.desc }}</span>
        </div>
      </div>
    </div>

    <!-- Search -->
    <div class="ep-search">
      <el-input v-model="searchQuery" placeholder="搜索专家角色名称或描述..." size="small" clearable :prefix-icon="Search" />
    </div>

    <!-- Favorites strip -->
    <div v-if="expertStore.favoriteRoles.length > 0" class="ep-fav-strip">
      <div class="ep-fav-header">
        <el-icon size="14"><StarFilled /></el-icon>
        <span>收藏专家</span>
      </div>
      <div class="ep-fav-items">
        <div v-for="fr in expertStore.favoriteRoles" :key="fr.role.id" class="ep-fav-chip" @click="summonRole(fr.role, fr.group)">
          <span>{{ fr.role.icon }}</span>
          <span class="ep-fav-name">{{ fr.role.name }}</span>
          <el-icon class="ep-fav-del" size="12" @click.stop="expertStore.toggleFavorite(fr.role.id)"><Close /></el-icon>
        </div>
      </div>
    </div>

    <!-- Group cards -->
    <div class="ep-groups">
      <div
        v-for="group in finalGroups" :key="group.id"
        :class="['ep-group-card', { expanded: currentExpanded.has(group.id) }]"
        @click="toggleGroup(group.id)"
      >
        <div class="ep-group-header">
          <span class="ep-group-icon">{{ group.icon }}</span>
          <div class="ep-group-info">
            <span class="ep-group-name">{{ group.name }}</span>
            <span class="ep-group-desc">{{ group.description }}</span>
          </div>
          <span class="ep-group-count">{{ group.roles.length }}个角色</span>
          <el-button size="small" round type="primary" class="ep-summon-btn"
            @click.stop="summonGroup(group)">
            <el-icon><UserFilled /></el-icon> 召唤
          </el-button>
          <el-icon :class="['ep-chevron', { rotated: currentExpanded.has(group.id) }]">
            <ArrowDown />
          </el-icon>
        </div>

        <!-- Role grid (expandable) -->
        <Transition name="ep-expand">
          <div v-if="currentExpanded.has(group.id)" class="ep-roles">
            <div
              v-for="role in group.roles" :key="role.id"
              class="ep-role-card"
              @click.stop="summonRole(role, group)"
            >
              <div class="ep-role-icon" :style="{ background: role.color + '18', color: role.color }">
                <span>{{ role.icon }}</span>
              </div>
              <div class="ep-role-body">
                <div class="ep-role-name">{{ role.name }}</div>
                <div class="ep-role-desc">{{ role.description }}</div>
                <span v-if="expertStore.getUsage(role.id) > 0" class="ep-role-usage">{{ expertStore.getUsage(role.id) }}次</span>
              </div>
              <el-button size="small" round class="ep-role-btn"
                @click.stop="summonRole(role, group)">
                召唤
              </el-button>
              <el-button size="small" text class="ep-role-fav" @click.stop="expertStore.toggleFavorite(role.id)">
                <el-icon><StarFilled v-if="expertStore.isFavorite(role.id)" /><Star v-else /></el-icon>
              </el-button>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ArrowDown, UserFilled, StarFilled, Star, Close, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useExpertStore } from '../stores/expert'
import { useChatStore } from '../stores/chat'
import { useMatterStore } from '../stores/matter'
import type { ExpertRole, ExpertGroup, ExpertCategory } from '../types/legal'

const emit = defineEmits<{
  'enter-chat': [sessionId: string]
}>()

const expertStore = useExpertStore()
const chatStore = useChatStore()
const matterStore = useMatterStore()

const activeCategory = ref<ExpertCategory>('litigation')
const expandedByCategory = ref<Record<string, string[]>>({})
const searchQuery = ref('')

const categories = [
  { key: 'litigation' as const, icon: '⚖️', name: '诉讼类', desc: '民事、刑事、行政、仲裁' },
  { key: 'industry' as const, icon: '🏢', name: '行业类', desc: '建设工程、知识产权、金融、医疗' },
  { key: 'corporate' as const, icon: '🏛️', name: '公司类', desc: '公司治理、劳动人事、合同、合规' },
]

const finalGroups = computed(() => {
  const base = expertStore.getGroupsByCategory(activeCategory.value)
  if (!searchQuery.value.trim()) return base

  const results = expertStore.searchRoles(searchQuery.value)
  const groupIds = new Set(results.map(r => r.group.id))
  const groupsWithMatches = base.filter(g => groupIds.has(g.id))

  // Auto-expand matching groups
  const currentCat = activeCategory.value
  const current = expandedByCategory.value[currentCat] || []
  for (const g of groupsWithMatches) {
    if (!current.includes(g.id)) current.push(g.id)
  }
  expandedByCategory.value[currentCat] = current

  return groupsWithMatches.map(g => ({
    ...g,
    roles: g.roles.filter(r => results.some(res => res.role.id === r.id)),
  }))
})

const currentExpanded = computed(() => {
  return new Set(expandedByCategory.value[activeCategory.value] || [])
})

function toggleGroup(id: string) {
  const cat = activeCategory.value
  const current = expandedByCategory.value[cat] || []
  const set = new Set(current)
  if (set.has(id)) set.delete(id); else set.add(id)
  expandedByCategory.value[cat] = Array.from(set)
}

function summonRole(role: ExpertRole, group: ExpertGroup) {
  expertStore.recordUsage(role.id)
  chatStore.newSessionWithExpert(role, matterStore.activeMatterId || undefined)
  // 示例问题预填输入框但不自动发送（是否补充案件细节由用户决定）
  if (role.samplePrompt) {
    chatStore.setPendingPrefill(role.samplePrompt)
  }
  ElMessage.success(`已召唤「${role.name}」（${group.name}）`)
  emit('enter-chat', chatStore.activeSessionId!)
}

function summonGroup(group: ExpertGroup) {
  // Build combined prompt with detailed role instructions
  const roleSummaries = group.roles.map(r =>
    `- ${r.icon} ${r.name}：${r.description}`
  ).join('\n')

  const detailedRoles = group.roles.map(r =>
    `\n## ${r.icon} ${r.name}\n${r.systemPrompt}`
  ).join('')

  const groupPrompt = `你是一个综合法律专家团队，汇集了${group.name}的全部专业能力。\n\n该团队包含以下专家角色：\n${roleSummaries}\n\n各专家详细能力说明：${detailedRoles}\n\n请根据用户的问题，以最合适的专家角色身份进行回答。如果需要多角色协作（如先研究后起草），请自动协调。`

  chatStore.newSession()
  const s = chatStore.activeSession
  if (s) {
    s.title = group.name + '（整团）'
    s.systemPrompt = groupPrompt
    s.expertRoleId = ''
  }
  ElMessage.success(`已召唤「${group.name}」整团`)
  emit('enter-chat', chatStore.activeSessionId!)
}
</script>

<style scoped>
.expert-page {
  padding: 24px 28px 40px;
  overflow: visible;    /* 外层 view-slot--page-scroll 统一提供唯一滚动条 */
  height: auto;
  min-height: 100%;
  max-width: 1100px;
  margin: 0 auto;
}

.page-title { margin: 0; font-size: 22px; color: var(--legal-navy); }
.page-subtitle { margin: 4px 0 0; color: var(--legal-text-secondary); font-size: 13px; }

/* ── Category tabs ── */
.ep-categories {
  display: flex;
  gap: 10px;
  margin: 20px 0;
}

.ep-cat-tab {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-radius: var(--radius-lg);
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: all var(--transition-base);
}

.ep-cat-tab:hover {
  border-color: var(--legal-gold);
  box-shadow: var(--shadow-sm);
}

.ep-cat-tab.active {
  border-color: var(--legal-gold);
  background: var(--legal-gold-bg);
  box-shadow: var(--shadow-sm);
}

.ep-cat-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.ep-cat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ep-cat-name {
  font-weight: var(--weight-semibold);
  font-size: 15px;
  color: var(--legal-navy);
}

.ep-cat-desc {
  font-size: 12px;
  color: var(--legal-text-muted);
}

/* ── Search ── */
.ep-search { margin: 12px 0; }

/* ── Favorites strip ── */
.ep-fav-strip {
  background: var(--legal-gold-bg);
  border: 1px solid var(--legal-gold-lighter);
  border-radius: var(--radius-lg);
  padding: 10px 14px;
  margin-bottom: 16px;
}
.ep-fav-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--legal-gold-dark);
  margin-bottom: 8px;
}
.ep-fav-items { display: flex; gap: 6px; flex-wrap: wrap; }
.ep-fav-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 14px;
  background: var(--legal-bg-card);
  border: 1px solid var(--legal-gold-lighter);
  cursor: pointer; font-size: 12px;
  transition: all var(--transition-fast);
}
.ep-fav-chip:hover { border-color: var(--legal-gold); }
.ep-fav-name { font-weight: 500; }
.ep-fav-del { opacity: 0.3; cursor: pointer; }
.ep-fav-del:hover { opacity: 1; color: var(--legal-danger); }

/* ── Group cards ── */
.ep-groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ep-group-card {
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all var(--transition-base);
  cursor: pointer;
}

.ep-group-card:hover {
  border-color: var(--legal-border);
  box-shadow: var(--shadow-sm);
}

.ep-group-card.expanded {
  border-color: var(--legal-navy);
  box-shadow: var(--shadow-sm);
}

.ep-group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
}

.ep-group-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.ep-group-info {
  flex: 1;
  min-width: 0;
}

.ep-group-name {
  font-size: 15px;
  font-weight: var(--weight-semibold);
  color: var(--legal-navy);
  display: block;
  margin-bottom: 2px;
}

.ep-group-desc {
  font-size: 12px;
  color: var(--legal-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ep-group-count {
  font-size: 12px;
  color: var(--legal-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}

.ep-chevron {
  color: var(--legal-text-muted);
  transition: transform var(--transition-fast);
  flex-shrink: 0;
}

.ep-chevron.rotated {
  transform: rotate(180deg);
}

/* ── Role grid ── */
.ep-roles {
  border-top: 1px solid var(--el-border-color-lighter);
  padding: 12px 16px 16px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.ep-role-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--el-border-color-extra-light);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ep-role-card:hover {
  border-color: var(--legal-navy);
  background: var(--legal-navy-bg);
  box-shadow: var(--shadow-sm);
}

.ep-role-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.ep-role-body {
  flex: 1;
  min-width: 0;
}

.ep-role-name {
  font-size: 13px;
  font-weight: var(--weight-medium);
  color: var(--legal-text);
  margin-bottom: 2px;
}

.ep-role-desc {
  font-size: 11px;
  color: var(--legal-text-muted);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ep-role-btn {
  flex-shrink: 0;
  font-size: 12px;
  padding: 4px 12px;
}

.ep-summon-btn {
  flex-shrink: 0;
  font-size: 12px;
  padding: 4px 12px;
  margin-right: 4px;
}

/* ── Usage badge ── */
.ep-role-usage {
  font-size: 10px;
  color: var(--legal-text-muted);
  background: var(--el-fill-color);
  padding: 0 6px;
  border-radius: 8px;
  line-height: 16px;
  flex-shrink: 0;
  margin-left: 4px;
}

/* ── Favorite button ── */
.ep-role-fav {
  flex-shrink: 0;
  padding: 2px !important;
  font-size: 14px !important;
  color: var(--legal-text-muted);
}
.ep-role-fav:hover { color: var(--legal-gold); }

/* ── Transition ── */
.ep-expand-enter-active {
  transition: opacity 0.15s ease, max-height 0.25s ease;
  max-height: 600px;
}
.ep-expand-leave-active {
  transition: opacity 0.1s ease, max-height 0.2s ease;
  max-height: 0;
}
.ep-expand-enter-from,
.ep-expand-leave-to {
  opacity: 0;
  max-height: 0;
}

/* ── Dark mode ── */
[data-theme="dark"] .ep-fav-strip {
  background: rgba(212,168,67,0.08);
  border-color: rgba(212,168,67,0.2);
}
[data-theme="dark"] .ep-fav-chip {
  background: var(--legal-bg-card);
  border-color: var(--legal-border);
}
</style>
