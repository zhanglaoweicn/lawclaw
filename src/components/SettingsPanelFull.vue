<template>
  <div class="settings-view">
    <div class="sv-header">
      <h3>配置</h3>
      <el-button text @click="$emit('close')">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
    </div>
    <div class="sv-body">
      <el-tabs v-model="activeTab" tab-position="left" class="sv-tabs">
        <el-tab-pane label="模型配置" name="model">
          <el-form label-position="top">
            <!-- Provider preset -->
            <el-form-item label="API 提供商">
              <el-select v-model="selectedPreset" placeholder="选择预设提供商（可选）" style="width:100%" clearable @change="onPresetChange">
                <el-option v-for="p in PROVIDER_PRESETS" :key="p.label" :label="p.label" :value="p.label" />
              </el-select>
              <div class="form-hint">选择后将自动填充 API 地址和模型名称</div>
            </el-form-item>
            <el-form-item label="API 地址">
              <el-input v-model="form.baseUrl" placeholder="https://api.openai.com/v1" />
            </el-form-item>
            <el-form-item label="模型名称">
              <el-input v-model="form.model" placeholder="deepseek-flash" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="form.apiKey" type="password" show-password placeholder="sk-..." />
            </el-form-item>
            <el-form-item>
              <div class="test-row">
                <el-button :loading="testingConnection" type="default" @click="testConnection">
                  <el-icon><Connection /></el-icon> 测试连接
                </el-button>
                <span class="test-hint">验证 API 地址和 Key 是否可用</span>
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="消息通道" name="messaging">
          <h4 style="margin:0 0 12px;color:var(--legal-navy);font-size:14px;">飞书</h4>
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
                <div class="form-hint">修改此字段将替换已保存的 Secret；留空则保留原有值</div>
              </el-form-item>
            </template>
          </el-form>

          <h4 style="margin:20px 0 12px;color:var(--legal-navy);font-size:14px;">企业微信</h4>
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
                <div class="form-hint">修改此字段将替换已保存的 Secret；留空则保留原有值</div>
              </el-form-item>
            </template>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="律师信息" name="profile">
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
                  <div class="years-input">
                    <el-input-number v-model="form.years" :min="0" :max="50" style="width:100%" />
                    <span class="years-unit">年</span>
                  </div>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="业务领域（可多选）">
              <el-checkbox-group v-model="form.practiceAreas">
                <el-checkbox label="民商事诉讼" />
                <el-checkbox label="合同纠纷" />
                <el-checkbox label="劳动人事" />
                <el-checkbox label="知识产权" />
                <el-checkbox label="公司并购" />
                <el-checkbox label="房地产与建设工程" />
                <el-checkbox label="婚姻家事" />
                <el-checkbox label="刑事辩护" />
                <el-checkbox label="行政诉讼" />
                <el-checkbox label="常年法律顾问" />
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
        </el-tab-pane>

        <el-tab-pane label="数据源 (MCP)" name="datasource">
          <div v-if="mcpLoading" style="text-align:center;padding:40px 0;color:var(--legal-text-muted)">
            <el-icon class="is-loading" size="20"><Loading /></el-icon>
            <p style="margin:8px 0 0;font-size:13px">正在加载数据源...</p>
          </div>
          <div v-else-if="mcpError" style="text-align:center;padding:40px 0;color:var(--legal-danger)">
            <p style="font-size:13px">{{ mcpError }}</p>
            <el-button size="small" style="margin-top:8px" @click="loadMcpServers">重试</el-button>
          </div>
          <div v-else-if="mcpServers.length === 0" style="text-align:center;padding:40px 0;color:var(--legal-text-muted)">
            <p style="font-size:13px">暂无配置的数据源</p>
          </div>
          <div v-else class="mcp-list">
            <div v-for="s in mcpServers" :key="s.name" class="mcp-card">
              <div class="mcp-card-top">
                <el-tag :type="s.enabled ? 'success' : 'info'" size="small" effect="plain">
                  {{ s.enabled ? '已启用' : '已禁用' }}
                </el-tag>
                <span class="mcp-name">{{ s.name }}</span>
              </div>
              <div class="mcp-url">{{ s.url }}</div>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="外观" name="appearance">
          <h4 style="margin:0 0 12px;color:var(--legal-navy);font-size:14px;">主题</h4>
          <div class="theme-selector">
            <div :class="['theme-option', { active: themeStore.theme === 'light' }]"
              @click="themeStore.setTheme('light')">
              <div class="theme-preview theme-preview-light">
                <div class="tp-icon"><el-icon><Sunny /></el-icon></div>
              </div>
              <span class="theme-label">亮色模式</span>
            </div>
            <div :class="['theme-option', { active: themeStore.theme === 'dark' }]"
              @click="themeStore.setTheme('dark')">
              <div class="theme-preview theme-preview-dark">
                <div class="tp-icon"><el-icon><Moon /></el-icon></div>
              </div>
              <span class="theme-label">暗色模式</span>
            </div>
          </div>
          <p style="margin:16px 0 0;font-size:12px;color:var(--legal-text-muted);">
            切换应用外观，也可跟随系统偏好自动切换。
          </p>
        </el-tab-pane>
      </el-tabs>
    </div>
    <div class="sv-footer">
      <el-button @click="$emit('close')">取消</el-button>
      <el-button type="primary" @click="handleSave">保存</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ArrowLeft, Loading, Sunny, Moon, Connection } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useThemeStore } from '../stores/theme'
import { useSettingsForm } from '../composables/useSettingsForm'
import { backend } from '../lib/backend'

const themeStore = useThemeStore()

defineEmits<{ close: [] }>()

const {
  activeTab, form, mcpServers, mcpLoading, mcpError, testingConnection,
  loadFromStore, save, testConnection, loadMcpServers,
  PROVIDER_PRESETS, applyPreset, SECRET_PLACEHOLDER,
} = useSettingsForm()

onMounted(() => {
  loadFromStore()
  loadMcpServers()
})

async function handleSave() {
  await save()
  // Verify connectivity
  try {
    const info = await backend.call<{ status: string; configured: boolean; model: string }>('initialize', {
      api_key: form.apiKey, base_url: form.baseUrl, model: form.model,
    })
    if (info.configured) {
      ElMessage.success(`设置已保存，后端就绪（${info.model}）`)
    } else {
      ElMessage.warning('设置已保存，但 API Key 未配置或无效')
    }
  } catch {
    ElMessage.success('设置已保存（后端连接测试未通过，请确认引擎已启动）')
  }
}

const selectedPreset = ref('')

function onPresetChange(val: string) {
  if (!val) return
  const preset = PROVIDER_PRESETS.find(p => p.label === val)
  if (preset) applyPreset(preset)
}
</script>

<style scoped>
.settings-view {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--legal-bg-card);
}
.sv-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--el-border-color-light);
}
.sv-header h3 {
  margin: 0;
  font-size: 17px;
  font-family: var(--font-heading);
  color: var(--legal-navy);
}
/* 主体：左侧菜单（固定宽）+ 右侧内容（自适应铺满，内部限宽） */
.sv-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 12px 16px 0;
  display: flex;
}
.sv-footer {
  padding: 12px 24px;
  border-top: 1px solid var(--el-border-color-light);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.sv-tabs {
  flex: 1;
  min-width: 0;
  display: flex;
}
/* 左侧菜单：固定宽 + 药丸选中态（修复底色整列溢出） */
.sv-tabs :deep(.el-tabs__header.is-left) {
  width: 176px;
  flex-shrink: 0;
  margin-right: 20px;
}
.sv-tabs :deep(.el-tabs__nav-wrap.is-left)::after { display: none; }
.sv-tabs :deep(.el-tabs__active-bar.is-left) { display: none; }
.sv-tabs :deep(.el-tabs__item.is-left) {
  height: 40px;
  line-height: 40px;
  padding: 0 16px;
  text-align: left;
  border-radius: 8px;
  margin: 2px 0;
  color: var(--legal-text-secondary);
  justify-content: flex-start;
}
.sv-tabs :deep(.el-tabs__item.is-left:hover) { color: var(--legal-navy); background: var(--legal-navy-bg); }
.sv-tabs :deep(.el-tabs__item.is-left.is-active) {
  background: var(--legal-navy-bg);
  color: var(--legal-navy);
  font-weight: 600;
}
/* 右侧内容：铺满剩余宽度，内部限宽可读 */
.sv-tabs :deep(.el-tabs__content.is-left) {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 8px 32px 28px 8px;
}
.sv-tabs :deep(.el-tab-pane) { max-width: 720px; }

.mcp-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mcp-card {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--el-border-color-lighter);
  background: var(--legal-bg-card);
}

.mcp-card-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.mcp-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--legal-navy);
}

.mcp-url {
  font-size: 12px;
  color: var(--legal-text-muted);
  word-break: break-all;
}

/* ── Theme selector ── */
.theme-selector {
  display: flex;
  gap: 16px;
  margin-top: 4px;
}

.theme-option {
  flex: 1;
  border: 2px solid var(--el-border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.theme-option:hover {
  border-color: var(--legal-text-muted);
}

.theme-option.active {
  border-color: var(--legal-gold);
  box-shadow: 0 0 0 1px var(--legal-gold);
}

.theme-preview {
  width: 100%;
  height: 80px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.theme-preview-light {
  background: #f2f3f7;
  border: 1px solid #d0d2db;
}

.theme-preview-dark {
  background: #0d1117;
  border: 1px solid #30363d;
}

.tp-icon {
  font-size: 24px;
}

.theme-preview-light .tp-icon { color: #b8973e; }
.theme-preview-dark .tp-icon { color: #d4a843; }

.theme-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--legal-text);
}

.form-hint {
  font-size: 11px;
  color: var(--legal-text-muted);
  margin-top: 4px;
  line-height: 1.4;
}

.test-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.test-hint {
  font-size: 12px;
  color: var(--legal-text-muted);
}

.years-input {
  display: flex;
  align-items: center;
  gap: 4px;
}

.years-unit {
  font-size: 13px;
  color: var(--legal-text-secondary);
  white-space: nowrap;
}
</style>