<template>
  <div class="nav-sidebar" :class="{ 'is-collapsed': collapsed }">
    <div
      class="sidebar-brand"
      @click="collapsed ? $emit('toggle-collapse') : $emit('navigate', 'dashboard')"
      :style="{ cursor: 'pointer' }"
      :title="collapsed ? '展开侧边栏（Ctrl+\\）' : '返回工作台'"
    >
      <span class="brand-icon">&#x2696;</span>
      <div class="brand-text" v-show="!collapsed">
        <span class="brand-name">LawClaw</span>
        <span class="brand-zh">律爪</span>
      </div>
      <el-button
        v-if="!collapsed"
        text
        class="collapse-btn collapse-btn-inline"
        @click.stop="$emit('toggle-collapse')"
        aria-label="折叠侧边栏"
      >
        <el-icon><Fold /></el-icon>
      </el-button>
    </div>

    <el-menu
      :default-active="activeView"
      :collapse="collapsed"
      :collapse-transition="false"
      class="nav-menu"
      @select="onSelect"
    >
      <el-menu-item index="assistant">
        <el-tooltip v-if="collapsed" content="助理" placement="right" :show-after="200">
          <el-icon style="width:100%;display:inline-flex;justify-content:center"><ChatDotRound /></el-icon>
        </el-tooltip>
        <template v-else>
          <el-icon><ChatDotRound /></el-icon>
          <span>助理</span>
        </template>
      </el-menu-item>

      <el-menu-item index="skills">
        <el-tooltip v-if="collapsed" content="技能" placement="right" :show-after="200">
          <el-icon style="width:100%;display:inline-flex;justify-content:center"><Lightning /></el-icon>
        </el-tooltip>
        <template v-else>
          <el-icon><Lightning /></el-icon>
          <span>技能</span>
        </template>
      </el-menu-item>

      <el-menu-item index="experts">
        <el-tooltip v-if="collapsed" content="专家" placement="right" :show-after="200">
          <el-icon style="width:100%;display:inline-flex;justify-content:center"><UserFilled /></el-icon>
        </el-tooltip>
        <template v-else>
          <el-icon><UserFilled /></el-icon>
          <span>专家</span>
        </template>
      </el-menu-item>

      <el-menu-item index="calendar">
        <el-tooltip v-if="collapsed" content="日程" placement="right" :show-after="200">
          <el-icon style="width:100%;display:inline-flex;justify-content:center"><Calendar /></el-icon>
        </el-tooltip>
        <template v-else>
          <el-icon><Calendar /></el-icon>
          <span>日程</span>
        </template>
      </el-menu-item>

      <el-menu-item index="cases">
        <el-tooltip v-if="collapsed" content="案件" placement="right" :show-after="200">
          <el-icon style="width:100%;display:inline-flex;justify-content:center"><Files /></el-icon>
        </el-tooltip>
        <template v-else>
          <el-icon><Files /></el-icon>
          <span>案件</span>
        </template>
      </el-menu-item>

      <el-menu-item index="files">
        <el-tooltip v-if="collapsed" content="文件" placement="right" :show-after="200">
          <el-icon style="width:100%;display:inline-flex;justify-content:center"><FolderOpened /></el-icon>
        </el-tooltip>
        <template v-else>
          <el-icon><FolderOpened /></el-icon>
          <span>文件</span>
        </template>
      </el-menu-item>
    </el-menu>

    <div class="sidebar-footer">
      <div class="footer-row">
        <el-tooltip
          v-if="collapsed"
          :content="connected ? '后端已就绪' : '后端未连接（点此进入配置）'"
          placement="right"
          :show-after="300"
        >
          <div
            :class="['status-dot', 'status-dot--collapsed', connected ? 'connected' : 'disconnected']"
            @click="connected ? undefined : $emit('navigate', 'settings')"
            :style="connected ? {} : { cursor: 'pointer' }"
            :aria-label="connected ? '已连接' : '未连接'"
          ></div>
        </el-tooltip>
        <template v-else>
          <div
            :class="['status-dot', connected ? 'connected' : 'disconnected']"
            @click="connected ? undefined : $emit('navigate', 'settings')"
            :style="connected ? {} : { cursor: 'pointer' }"
          >
            <span class="status-text">{{ connected ? '已就绪' : '未连接' }}</span>
          </div>
          <el-tooltip :content="themeStore.theme === 'dark' ? '切换亮色' : '切换暗色'" placement="top">
            <el-button text size="small" class="theme-toggle-btn" @click="themeStore.toggleTheme()" aria-label="切换主题">
              <el-icon><Sunny v-if="themeStore.theme === 'light'" /><Moon v-else /></el-icon>
            </el-button>
          </el-tooltip>
        </template>
      </div>

      <div
        v-show="!collapsed"
        class="footer-settings"
        @click="$emit('navigate', 'settings')"
      >
        <el-icon><Setting /></el-icon>
        <span>配置</span>
      </div>
      <el-tooltip v-if="collapsed" content="配置" placement="right" :show-after="300">
        <div
          class="footer-settings footer-settings--collapsed"
          @click="$emit('navigate', 'settings')"
        >
          <el-icon><Setting /></el-icon>
        </div>
      </el-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Fold, Calendar, ChatDotRound, Files, FolderOpened, Setting, Sunny, Moon, UserFilled, Lightning } from '@element-plus/icons-vue'
import { useThemeStore } from '../stores/theme'

const themeStore = useThemeStore()

defineProps<{
  activeView: string
  connected: boolean
  collapsed: boolean
}>()

const emit = defineEmits<{
  navigate: [view: string]
  'toggle-collapse': []
}>()

function onSelect(index: string) {
  emit('navigate', index)
}
</script>

<style scoped>
.nav-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0; /* 折叠态时允许收缩到 64px */
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 14px 10px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  margin-bottom: 4px;
  user-select: none;
}

.brand-icon {
  font-size: 22px;
  line-height: 1;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  color: var(--legal-navy);
}

.brand-text {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  font-family: var(--font-heading);
  color: var(--legal-navy);
  line-height: 1.15;
  letter-spacing: 0.3px;
}

.brand-zh {
  font-size: 11px;
  color: var(--legal-gold);
  font-weight: 500;
  letter-spacing: 1.5px;
  margin-top: 1px;
}

/* 侧边栏内折叠按钮 */
.collapse-btn {
  color: var(--legal-text-secondary);
  padding: 4px;
  font-size: 14px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.collapse-btn:hover {
  color: var(--legal-navy);
  background: var(--el-fill-color-light);
}
.collapse-btn-inline {
  margin-left: auto;
}

/* 折叠态：brand 区居中图标 */
.nav-sidebar.is-collapsed .sidebar-brand {
  padding: 14px 0 10px;
  justify-content: center;
  gap: 0;
  flex-direction: row;      /* 折叠态保持单行：仅 logo，点击整行展开 */
  border-radius: var(--radius-sm);
  margin: 4px 8px 4px;
  padding: 12px 0;
  transition: background 0.15s;
}
.nav-sidebar.is-collapsed .sidebar-brand:hover {
  background: var(--el-fill-color-light);
}
.nav-sidebar.is-collapsed .brand-icon {
  width: 32px;
  height: 32px;
  font-size: 24px;
}

.nav-menu {
  border-right: none;
  --el-menu-item-height: 42px;
  background: transparent !important;
}

.nav-menu :deep(.el-menu-item) {
  position: relative;
  margin: 2px 6px;
  border-radius: var(--radius-sm);
  width: calc(100% - 12px) !important;
  color: var(--legal-text-secondary);
}

.nav-menu :deep(.el-menu-item:hover) {
  background: var(--el-fill-color-light) !important;
  color: var(--legal-navy);
}

.nav-menu :deep(.el-menu-item.is-active) {
  color: var(--legal-gold-dark);
  background: color-mix(in srgb, var(--legal-gold-bg) 92%, white);
  font-weight: 600;
}

.nav-menu :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: -6px; /* 抵消 6px margin */
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: linear-gradient(180deg, var(--legal-gold-light), var(--legal-gold-dark));
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  box-shadow: 0 0 4px rgba(var(--legal-gold-rgb, 201, 168, 76), 0.25);
}

/* 折叠态菜单：图标居中，无文字 padding 异常 */
.nav-sidebar.is-collapsed .nav-menu :deep(.el-menu-item) {
  margin: 2px auto;
  width: 42px !important;
  height: 42px;
  padding: 0 !important;
  justify-content: center !important;
  display: flex;
  align-items: center;
}
.nav-sidebar.is-collapsed .nav-menu :deep(.el-menu-item .el-icon) {
  margin: 0 !important;
}
.nav-sidebar.is-collapsed .nav-menu :deep(.el-menu-item.is-active::before) {
  /* 折叠态激活条：变顶部横条（左侧没意义） */
  left: 0;
  right: 0;
  top: 0;
  bottom: auto;
  height: 3px;
  width: auto;
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}

.sidebar-footer {
  margin-top: auto;
  padding: 8px 10px 10px;
  border-top: 1px solid var(--el-border-color-light);
  font-size: 12px;
  color: var(--legal-text-muted);
}

.footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  margin-bottom: 6px;
}

.footer-settings {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--legal-text-secondary);
  transition: background var(--transition-fast), color var(--transition-fast);
}

.footer-settings:hover {
  background: var(--el-fill-color-light);
  color: var(--legal-navy);
}

.footer-settings--collapsed {
  justify-content: center;
  padding: 8px 0;
  margin-top: 4px;
  width: 100%;
}

.status-dot {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
  flex: 1;
  min-width: 0;
  font-size: 12px;
}
.status-dot:hover { background: var(--el-fill-color-light); }

.status-dot--collapsed {
  justify-content: center;
  width: 28px;
  height: 28px;
  margin: 0 auto;
  flex: 0 0 auto;
  padding: 0;
  gap: 0;
}
.status-dot--collapsed::before { margin: 0 !important; }

.theme-toggle-btn {
  color: var(--legal-text-muted);
  flex-shrink: 0;
  padding: 2px;
}
.theme-toggle-btn:hover { color: var(--legal-gold); }

.status-dot::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
  margin-right: 2px;
}
.status-dot.connected::before {
  background: var(--legal-success);
  box-shadow: 0 0 4px rgba(var(--legal-success-rgb, 45, 125, 78), 0.45);
}
.status-dot.disconnected::before {
  background: var(--legal-danger);
  box-shadow: 0 0 4px rgba(var(--legal-danger-rgb, 178, 34, 34), 0.35);
}

.status-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
