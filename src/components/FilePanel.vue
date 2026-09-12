<template>
  <div class="file-panel"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop">
    <!-- Drop zone overlay -->
    <transition name="drop-fade">
      <div v-if="isDragging" class="drop-zone">
        <div class="drop-zone-content">
          <el-icon size="40"><Upload /></el-icon>
          <p>释放文件以上传</p>
        </div>
      </div>
    </transition>

    <div class="file-header">
      <h3>文件管理</h3>
      <div class="file-actions">
        <el-button type="primary" size="small" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon> 上传文件
        </el-button>
        <el-select v-model="filterMatterId" placeholder="全部案件" size="small" style="width:140px" clearable @change="onFilterMatterChange">
          <el-option v-for="m in matterStore.matters" :key="m.id" :label="m.title" :value="m.id" />
        </el-select>
        <el-select v-model="filterCategory" placeholder="全部分类" size="small" style="width:130px" clearable>
          <el-option v-for="c in availableCategories" :key="c" :label="c" :value="c" />
        </el-select>
      </div>
    </div>

    <div class="file-body">
      <!-- Left side: tree navigation -->
      <div class="file-tree-panel">
        <div class="file-tree-search">
          <el-input v-model="treeSearch" placeholder="搜索案件/文件..." size="small" clearable :prefix-icon="Search" />
        </div>
        <el-tree
          ref="fileTreeRef"
          :data="fileTreeData"
          :props="{ label: 'label', children: 'children' }"
          node-key="id"
          default-expand-all
          highlight-current
          @node-click="onTreeNodeClick"
          class="file-tree"
        >
          <template #default="{ data }">
            <span class="tree-node">
              <el-icon size="14">
                <FolderOpened v-if="data.type === 'matter' || data.type === 'category'" />
                <Document v-else />
              </el-icon>
              <span class="tree-label">{{ data.label }}</span>
              <span v-if="data.count" class="tree-count">{{ data.count }}</span>
              <span v-if="data.isAiGen" class="tree-ai-tag">AI</span>
            </span>
          </template>
        </el-tree>
      </div>

      <!-- Right side: file list + preview/editor -->
      <div class="file-content" :class="{ 'has-preview': !!previewFile }">
        <div class="fc-list">
          <div class="file-stats">
            <div class="file-stat" v-for="c in availableCategories" :key="c"
              :class="{ active: filterCategory === c }" @click="filterCategory = filterCategory === c ? '' : c">
              <span class="stat-num">{{ fileStore.filesByCategory(c).length }}</span>
              <span class="stat-label">{{ c }}</span>
              <el-icon v-if="c !== '案件文书' && c !== '证据材料' && c !== '其他'" size="12" class="stat-del"
                @click.stop="deleteCategory(c)">
                <Close />
              </el-icon>
            </div>
          </div>

          <div class="fc-summary">
            {{ filterMatterId ? `共 ${filteredFiles.length} 个文件` : `共 ${fileStore.files.length} 个文件` }}
          </div>

          <div v-if="filteredFiles.length === 0 && !previewFile" class="empty-state">
            <el-icon size="36" color="var(--legal-text-muted)"><FolderOpened /></el-icon>
            <p>暂无文件</p>
          </div>

          <!-- Batch action bar -->
          <transition name="drop-fade">
            <div v-if="selectedIds.size > 0" class="batch-bar">
              <span class="batch-info">已选 {{ selectedIds.size }} 项</span>
              <el-select v-model="batchCategory" placeholder="批量分类" size="small" style="width:130px"
                @change="onBatchCategorize" clearable>
                <el-option v-for="c in allCategoriesForBatch" :key="c" :label="c" :value="c" />
              </el-select>
              <el-popconfirm title="确认批量删除？" @confirm="onBatchDelete">
                <template #reference>
                  <el-button size="small" type="danger" text>
                    <el-icon><Delete /></el-icon> 批量删除
                  </el-button>
                </template>
              </el-popconfirm>
              <el-button size="small" text @click="selectedIds.clear()">取消选择</el-button>
            </div>
          </transition>

          <!-- Case-grouped view (no matter filter) -->
          <div v-if="filteredFiles.length > 0 && !filterMatterId" class="file-group-by-case">
            <div v-for="(files, matterId) in filesGroupedByMatter" :key="matterId" class="fg-case-group">
              <div class="fg-case-header">
                <el-icon><FolderOpened /></el-icon>
                <span class="fg-case-title">{{ matterMap[matterId] || '未关联案件' }}</span>
                <span class="fg-case-count">{{ files.length }} 个文件</span>
              </div>
              <div class="file-list">
                <div v-for="f in files" :key="f.id" class="file-row"
                  :class="{ 'is-selected': previewFile?.data === f.data }">
                  <div class="file-checkbox" @click.stop="toggleSelect(f.id)">
                    <el-checkbox :model-value="selectedIds.has(f.id)" size="small" />
                  </div>
                  <div class="file-click-area" @contextmenu.prevent="showCtxMenu($event, f)" @click="openPreview(f)">
                    <div class="file-icon" :class="fileTypeClass(f.name)">
                      <el-icon :size="20">
                        <Picture v-if="isImageFile(f.name)" />
                        <Document v-else-if="isDocFile(f.name)" />
                        <PieChart v-else-if="isSheetFile(f.name)" />
                        <Reading v-else-if="isPdfFile(f.name)" />
                        <FolderOpened v-else />
                      </el-icon>
                    </div>
                    <div class="file-info">
                      <div class="file-name">{{ f.name }}</div>
                      <div class="file-meta">
                        <el-tag size="small" effect="plain" type="info">{{ f.category }}</el-tag>
                        <el-tag v-if="f.extractedText" size="small" effect="dark" class="parsed-tag" title="已解析全文，AI 对话与全文搜索可用">✓ AI可读</el-tag>
                        <span>{{ (f.size / 1024).toFixed(1) }} KB</span>
                        <span>{{ formatDate(f.createdAt) }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="file-ops">
                    <el-select v-model="f.category" size="small" style="width:110px" @click.stop @change="onCategoryChange(f.id, $event)">
                      <el-option v-for="c in categoriesForMatter(f.matterId)" :key="c" :label="c" :value="c" />
                    </el-select>
                    <el-popconfirm title="确认删除？" @confirm="fileStore.deleteFile(f.id)">
                      <template #reference>
                        <el-button size="small" text type="danger" @click.stop>
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Flat file list (with matter filter) -->
          <div v-if="filteredFiles.length > 0 && filterMatterId" class="file-list">
            <div v-for="f in filteredFiles" :key="f.id" class="file-row"
              :class="{ 'is-selected': previewFile?.data === f.data }">
              <div class="file-checkbox" @click.stop="toggleSelect(f.id)">
                <el-checkbox :model-value="selectedIds.has(f.id)" size="small" />
              </div>
              <div class="file-click-area" @contextmenu.prevent="showCtxMenu($event, f)" @click="openPreview(f)">
                <div class="file-icon" :class="fileTypeClass(f.name)">
                  <el-icon :size="20">
                    <Picture v-if="isImageFile(f.name)" />
                    <Document v-else-if="isDocFile(f.name)" />
                    <PieChart v-else-if="isSheetFile(f.name)" />
                    <Reading v-else-if="isPdfFile(f.name)" />
                    <FolderOpened v-else />
                  </el-icon>
                </div>
                <div class="file-info">
                  <div class="file-name">{{ f.name }}</div>
                  <div class="file-meta">
                    <el-tag v-if="f.matterId && matterMap[f.matterId]" size="small" effect="plain" type="warning">
                      {{ matterMap[f.matterId] }}
                    </el-tag>
                    <el-tag size="small" effect="plain" type="info">{{ f.category }}</el-tag>
                    <el-tag v-if="f.extractedText" size="small" effect="dark" class="parsed-tag" title="已解析全文，AI 对话与全文搜索可用">✓ AI可读</el-tag>
                    <span>{{ (f.size / 1024).toFixed(1) }} KB</span>
                    <span>{{ formatDate(f.createdAt) }}</span>
                  </div>
                </div>
              </div>
              <div class="file-ops">
                <el-select v-model="f.category" size="small" style="width:110px" @click.stop @change="onCategoryChange(f.id, $event)">
                  <el-option v-for="c in categoriesForMatter(f.matterId)" :key="c" :label="c" :value="c" />
                </el-select>
                <el-popconfirm title="确认删除？" @confirm="fileStore.deleteFile(f.id)">
                  <template #reference>
                    <el-button size="small" text type="danger" @click.stop>
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
          </div>
        </div>

        <!-- ═══ Inline preview / editor panel (right panel) ═══ -->
        <div v-if="previewFile" class="fc-preview">
          <div class="fcp-header">
            <span class="fcp-name">{{ previewFile.name }}</span>
            <div class="fcp-actions">
              <el-button v-if="isTextFile(previewFile.name) && !editing" size="small" text type="warning" @click="reviewCurrent">
                <el-icon><Search /></el-icon> 校对
              </el-button>
              <template v-if="isTextFile(previewFile.name) && isEditableFile(previewFile.name)">
                <el-button v-if="!editing" size="small" text @click="startEditing">
                  <el-icon><Edit /></el-icon> 编辑
                </el-button>
                <template v-else>
                  <el-button size="small" type="primary" @click="saveEdits" :loading="saving">
                    <el-icon><Check /></el-icon> 保存
                  </el-button>
                  <el-button size="small" text @click="cancelEditing">
                    <el-icon><Close /></el-icon> 取消
                  </el-button>
                </template>
              </template>
              <template v-if="isOfficeFile(previewFile.name)">
                <el-tag size="small" effect="plain" type="warning" class="fcp-office-tag">Word / PDF</el-tag>
              </template>
              <el-button size="small" text @click="downloadFile">
                <el-icon><Download /></el-icon> 下载
              </el-button>
              <el-button size="small" text @click="closePreview">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="fcp-body">
            <img v-if="isImageFile(previewFile.name) && !editing"
              :src="previewFile.data" class="fcp-image" alt="预览" />
            <textarea v-else-if="isTextFile(previewFile.name) && editing"
              v-model="editText" class="fcp-editor" spellcheck="false"></textarea>
            <pre v-else-if="previewFile.extractedText" class="pdf-text-preview">{{ previewFile.extractedText.slice(0, 20000) }}</pre>
            <div v-else-if="isTextFile(previewFile.name) || isOfficeFile(previewFile.name)"
              class="fcp-markdown" v-html="renderedMarkdown"></div>
            <div v-else class="fcp-placeholder">
              <el-icon size="48"><Document /></el-icon>
              <p class="fcp-name">{{ previewFile.name }}</p>
              <p class="fcp-meta">{{ (previewFile.size / 1024).toFixed(1) }} KB</p>
              <p class="fcp-hint">此类型暂不支持在线预览，请下载后查看</p>
            </div>
          </div>
        </div>
      </div>
  </div>


    <!-- Upload Dialog -->
    <el-dialog v-model="showUploadDialog" title="上传文件" width="460px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="选择文件" required>
          <input ref="fileInputRef" type="file" style="display:none"
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,.gif,.webp,.bmp,.svg,.txt,.md,.csv,.json,.xml,.yaml,.wps,.ofd"
            @change="onFilePicked" />
          <el-button @click="fileInputRef?.click()">
            <el-icon><Upload /></el-icon> 浏览文件
          </el-button>
          <span v-if="pendingFile" class="pending-file-name">{{ pendingFile.name }}</span>
        </el-form-item>
        <el-form-item label="所属案件" required>
          <el-select v-model="uploadMatterId" placeholder="选择案件" style="width:100%" @change="onUploadMatterChange">
            <el-option v-for="m in matterStore.matters" :key="m.id" :label="m.title" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="文件分类" required>
          <div class="category-row">
            <el-select v-model="uploadCategory" placeholder="选择分类" style="width:100%">
              <el-option v-for="c in uploadCategories" :key="c" :label="c" :value="c" />
            </el-select>
            <el-button v-if="uploadMatterId" size="small" text @click="showNewCategory = true">
              <el-icon><Plus /></el-icon>
            </el-button>
          </div>
          <div v-if="showNewCategory" class="new-category-row">
            <el-input v-model="newCategoryName" size="small" placeholder="新分类名称" @keyup.enter="addCustomCategory" />
            <el-button size="small" type="primary" @click="addCustomCategory">添加</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!pendingFile || !uploadMatterId" @click="confirmUpload">上传</el-button>
      </template>
    </el-dialog>

    <!-- 校对结果对话框 -->
    <el-dialog v-model="showReview" title="文书校对报告" width="640px" :close-on-click-modal="false">
      <div v-if="reviewLoading" style="text-align:center;padding:30px 0;color:var(--legal-text-muted)">
        <el-icon class="is-loading" size="20"><Loading /></el-icon>
        <p style="margin-top:8px;font-size:13px">正在按八维规则 + 法条时效校对…</p>
      </div>
      <template v-else>
        <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap">
          <el-tag v-if="reviewStats.by_severity['严重']" type="danger" effect="dark">严重 {{ reviewStats.by_severity['严重'] }}</el-tag>
          <el-tag v-if="reviewStats.by_severity['一般']" type="warning" effect="dark">一般 {{ reviewStats.by_severity['一般'] }}</el-tag>
          <el-tag v-if="reviewStats.by_severity['提示']" type="info" effect="plain">提示 {{ reviewStats.by_severity['提示'] }}</el-tag>
          <span style="font-size:12px;color:var(--legal-text-muted)">{{ reviewStats.chars }} 字 · {{ reviewStats.lines }} 行</span>
          <el-button size="small" text style="margin-left:auto" @click="copyReview">复制报告</el-button>
        </div>
        <div v-if="reviewIssues.length === 0" style="text-align:center;padding:24px 0;color:var(--legal-success)">
          ✓ 未发现问题（八维规则 + 法条时效全部通过）
        </div>
        <div v-else class="review-list">
          <div v-for="(it, i) in reviewIssues" :key="i" class="review-item" :class="'sev-' + it.severity">
            <div style="display:flex;gap:6px;align-items:center;margin-bottom:3px;flex-wrap:wrap">
              <el-tag size="small" :type="it.severity === '严重' ? 'danger' : it.severity === '一般' ? 'warning' : 'info'" effect="dark">{{ it.severity }}</el-tag>
              <el-tag size="small" effect="plain">{{ it.module }}</el-tag>
              <span style="font-size:11px;color:var(--legal-text-muted)">第 {{ it.line }} 行</span>
            </div>
            <div style="font-size:13px;color:var(--legal-text);margin-bottom:2px">{{ it.message }}</div>
            <div style="font-size:12px;color:var(--legal-text-secondary)">建议：{{ it.suggestion }}</div>
          </div>
        </div>
      </template>
    </el-dialog>
  <ContextMenu :visible="ctxVisible" :pos="ctxPos" :items="ctxMenuItems" @close="ctxVisible = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Upload, FolderOpened, Document, Delete, Plus, Picture, PieChart, Reading, Close, Download, Edit, Check, Search, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ContextMenu, { type ContextMenuItem } from './ContextMenu.vue'
import { useFileStore } from '../stores/fileStore'
import { useMatterStore } from '../stores/matter'
import { exportMarkdownAsDocx } from '../lib/docxExport'
import { useFileEditor } from '../composables/useFileEditor'

const fileStore = useFileStore()
const matterStore = useMatterStore()

const filterCategory = ref('')
const filterMatterId = ref('')

// ── Drag & drop state ──
const isDragging = ref(false)
let dragCounter = 0

function onDragEnter(e: DragEvent) {
  dragCounter++
  if (e.dataTransfer?.types.includes('Files')) {
    isDragging.value = true
  }
}

function onDragOver(e: DragEvent) {
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
}

function onDragLeave(_e: DragEvent) {
  dragCounter--
  if (dragCounter <= 0) {
    dragCounter = 0
    isDragging.value = false
  }
}

function onDrop(e: DragEvent) {
  dragCounter = 0
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (!files?.length) return

  // Require an active matter filter for drag-drop
  if (!filterMatterId.value) {
    ElMessage.warning('请先在左侧树或顶部下拉框选择一个案件，再拖拽文件')
    return
  }

  let queued = 0
  for (const file of Array.from(files)) {
    if (!fileStore.isAllowedFile(file.name)) {
      ElMessage.warning(`不支持的文件类型: ${file.name}`)
      continue
    }
    queued++
    const reader = new FileReader()
    reader.onload = (ev) => {
      const defaultCategory = fileStore.suggestCategory(file.name, filterMatterId.value)
      fileStore.addFile(
        file.name,
        ev.target?.result as string,
        file.type,
        defaultCategory,
        filterMatterId.value,
      ).catch(() => ElMessage.error(`文件「${file.name}」上传失败`))
    }
    reader.readAsDataURL(file)
  }
  if (queued > 0) ElMessage.success(`已加入上传队列 ${queued} 个文件`)
}

// ── File preview state ──
const previewFile = ref<{ name: string; data: string; size: number; type: string; extractedText?: string; extractor?: string } | null>(null)

// ── Context menu state ──
const ctxVisible = ref(false)
const ctxPos = ref({ x: 0, y: 0 })
const ctxFile = ref<any>(null)

function showCtxMenu(e: MouseEvent, f: any) {
  ctxPos.value = { x: e.clientX, y: e.clientY }
  ctxFile.value = f
  ctxVisible.value = true
}

function closePreview() {
  previewFile.value = null
}

// ── 文书校对 ──
const showReview = ref(false)
const reviewLoading = ref(false)
const reviewIssues = ref<Array<{ module: string; severity: string; message: string; suggestion: string; line: number; excerpt: string }>>([])
const reviewStats = ref({ chars: 0, lines: 0, by_module: {} as Record<string, number>, by_severity: {} as Record<string, number> })

async function reviewCurrent() {
  if (!previewFile.value) return
  showReview.value = true
  reviewLoading.value = true
  reviewIssues.value = []
  try {
    const text = decodeFileContent(previewFile.value.data)
    const r = await backend.reviewDocument(text)
    reviewIssues.value = r.issues
    reviewStats.value = r.stats
  } catch (e: any) {
    ElMessage.error((e?.message || '校对失败').slice(0, 60))
    showReview.value = false
  } finally {
    reviewLoading.value = false
  }
}

async function copyReview() {
  const lines = reviewIssues.value.map(i => `[${i.severity}] ${i.module}（第${i.line}行）${i.message}——建议：${i.suggestion}`)
  const text = `文书校对报告（${reviewStats.value.chars} 字，共 ${reviewIssues.value.length} 项问题）\n` + lines.join('\n')
  ;(await copyText(text)) ? ElMessage.success('报告已复制') : ElMessage.warning('复制失败')
}

function openPreview(f: { name: string; data: string; size: number; type: string }) {
  previewFile.value = f
}

function downloadFile() {
  if (!previewFile.value) return
  const a = document.createElement('a')
  a.href = previewFile.value.data
  a.download = previewFile.value.name
  a.click()
}

// ── Inline editor state (from shared composable) ──
import { renderMarkdown } from '../lib/markdown'
import { copyText } from '../lib/clipboard'
import { backend } from '../lib/backend'
import { dataUrlToText } from '../lib/encoding'

const editor = useFileEditor(
  fileStore,
  () => ElMessage.success('文件已保存'),
  () => ElMessage.warning('保存失败'),
)

const { editing, editText, saving, isTextFile } = editor

function startEditing() {
  if (previewFile.value) editor.startEditing(previewFile.value)
}
function cancelEditing() {
  editor.cancelEditing()
}
function saveEdits() {
  return editor.saveEdits(previewFile)
}

function isOfficeFile(name: string) {
  return /\.(doc|docx|xls|xlsx|ppt|pptx|pdf)$/i.test(name)
}

function isEditableFile(name: string) {
  return isTextFile(name)
}

const renderedMarkdown = computed(() => {
  if (!previewFile.value) return ''
  // Office files: skip markdown parsing, use binary detection directly
  if (isOfficeFile(previewFile.value.name)) {
    const raw = decodeFileContent(previewFile.value.data)
    const cleaned = raw.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '')
    if (cleaned.length < 100) return cleaned
    const printable = cleaned.replace(/[^\x20-\x7E一-鿿　-〿﻿\n\r\t]/g, '').length
    if (printable / Math.max(cleaned.length, 1) < 0.3) {
      return `<div style="text-align:center;padding:20px;color:var(--legal-text-muted)">
        <p style="font-size:14px;margin-bottom:8px">📄 此文件需下载后用 Word 打开</p>
        <p style="font-size:12px;opacity:0.7">${escapeHtml(previewFile.value.name)}</p>
      </div>`
    }
    return `<pre style="white-space:pre-wrap;font-size:12px;line-height:1.5">${escapeHtml(cleaned.slice(0, 5000))}</pre>`
  }
  if (!isTextFile(previewFile.value.name)) return ''
  return renderMarkdown(decodeFileContent(previewFile.value.data))
})

function decodeFileContent(dataUrl: string): string {
  return dataUrlToText(dataUrl)
}

function escapeHtml(text: string): string {
  return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
}

function isImageFile(name: string) {
  return /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(name)
}

function isDocFile(name: string) {
  return /\.(doc|docx|wps)$/i.test(name)
}

function isSheetFile(name: string) {
  return /\.(xls|xlsx|csv)$/i.test(name)
}

function isPdfFile(name: string) {
  return /\.pdf$/i.test(name)
}

function fileTypeClass(name: string) {
  if (isImageFile(name)) return 'file-type-image'
  if (isPdfFile(name)) return 'file-type-pdf'
  if (isDocFile(name)) return 'file-type-doc'
  if (isSheetFile(name)) return 'file-type-sheet'
  return ''
}

const treeSearch = ref('')
const fileTreeRef = ref<any>(null)

interface TreeNode {
  id: string
  label: string
  type: 'matter' | 'category' | 'file'
  count?: number
  children?: TreeNode[]
  isAiGen?: boolean
}

const fileTreeData = computed(() => {
  const nodes: TreeNode[] = []
  const search = treeSearch.value.toLowerCase().trim()

  // Collect all matter IDs that exist in the store
  const knownMatterIds = new Set(matterStore.matters.map(m => m.id))

  for (const m of matterStore.matters) {
    const matterFiles = fileStore.files.filter(f => f.matterId === m.id)
    if (matterFiles.length === 0 && !search) continue

    const filtered = search
      ? matterFiles.filter(f =>
          f.name.toLowerCase().includes(search) ||
          (f.extractedText || '').toLowerCase().includes(search))
      : matterFiles
    if (filtered.length === 0 && search) continue

    const catMap: Record<string, TreeNode> = {}
    for (const f of filtered) {
      const cat = f.category
      if (!catMap[cat]) {
        catMap[cat] = { id: `cat-${m.id}-${cat}`, label: cat, type: 'category' as const, children: [] }
      }
      catMap[cat].children!.push({
        id: f.id, label: f.name, type: 'file' as const, isAiGen: cat === 'AI生成',
      })
    }
    nodes.push({
      id: m.id, label: m.title, type: 'matter' as const, count: filtered.length,
      children: Object.values(catMap),
    })
  }

  // Orphan files (no matching matter in store)
  const orphans = fileStore.files.filter(f => !knownMatterIds.has(f.matterId))
  if (orphans.length > 0) {
    const catMap: Record<string, TreeNode> = {}
    for (const f of orphans) {
      const cat = f.category
      if (!catMap[cat]) {
        catMap[cat] = { id: `orphan-${cat}`, label: cat, type: 'category' as const, children: [] }
      }
      catMap[cat].children!.push({
        id: f.id, label: f.name, type: 'file' as const, isAiGen: cat === 'AI生成',
      })
    }
    nodes.push({
      id: 'orphan-group', label: '未关联案件', type: 'matter' as const, count: orphans.length,
      children: Object.values(catMap),
    })
  }

  return nodes
})

function onTreeNodeClick(data: TreeNode) {
  if (data.type === 'file') {
    const f = fileStore.files.find(x => x.id === data.id)
    if (f) openPreview(f)
  } else if (data.type === 'category') {
    // Category click: enter flat view filtered by this category
    filterCategory.value = data.label
    filterMatterId.value = ''  // Clear matter filter to stay in grouped view
  } else if (data.type === 'matter') {
    if (data.id === 'orphan-group') {
      // Show all orphan files - filterMatterId stays empty but we need a filter
      filterMatterId.value = ''
      filterCategory.value = ''
    } else {
      filterMatterId.value = data.id
      filterCategory.value = ''
    }
  }
}

const matterMap = computed(() => {
  const map: Record<string, string> = {}
  for (const m of matterStore.matters) map[m.id] = m.title
  return map
})

const filesGroupedByMatter = computed(() => {
  const groups: Record<string, typeof fileStore.files> = {}
  let source = fileStore.files
  if (filterCategory.value) source = source.filter(f => f.category === filterCategory.value)
  for (const f of source) {
    const key = f.matterId || 'unlinked'
    if (!groups[key]) groups[key] = []
    groups[key].push(f)
  }
  return groups
})

const availableCategories = computed(() => {
  if (filterMatterId.value) {
    return matterStore.categoriesForMatter(filterMatterId.value)
  }
  // 全局视图只展示默认分类 + 实际有文件归属的分类
  // （不平铺所有案件的自定义分类，避免统计条无限膨胀）
  const all = new Set<string>()
  for (const f of fileStore.files) all.add(f.category)
  return [...new Set(['案件文书', '证据材料', ...all])].filter(Boolean)
})

const filteredFiles = computed(() => {
  let result = fileStore.files
  if (filterCategory.value) result = result.filter(f => f.category === filterCategory.value)
  if (filterMatterId.value) result = result.filter(f => f.matterId === filterMatterId.value)
  return result
})

function categoriesForMatter(matterId: string): string[] {
  return matterStore.categoriesForMatter(matterId)
}

function onFilterMatterChange(val: string | undefined) {
  if (val) filterCategory.value = ''
}

function onCategoryChange(fileId: string, category: string) {
  fileStore.updateCategory(fileId, category)
}

function deleteCategory(cat: string) {
  // Remove this category from all matters that have it
  for (const m of matterStore.matters) {
    matterStore.removeCategory(m.id, cat)
  }
  // Recategorize files with this category to '其他'
  for (const f of fileStore.files) {
    if (f.category === cat) {
      fileStore.updateCategory(f.id, '其他' as any)
    }
  }
  if (filterCategory.value === cat) filterCategory.value = ''
  ElMessage.success(`已删除分类「${cat}」`)
}

// Upload dialog state
const showUploadDialog = ref(false)
const fileInputRef = ref<HTMLInputElement>()
const pendingFile = ref<{ name: string; data: string; type: string } | null>(null)
const uploadMatterId = ref('')
const uploadCategory = ref('其他')
const showNewCategory = ref(false)
const newCategoryName = ref('')

const uploadCategories = computed(() => {
  if (!uploadMatterId.value) return ['其他']
  return matterStore.categoriesForMatter(uploadMatterId.value)
})

// ── Multi-select ──
const selectedIds = ref(new Set<string>())
const batchCategory = ref('')

function toggleSelect(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id); else next.add(id)
  selectedIds.value = next
}

function onBatchCategorize(cat: string) {
  if (!cat) return
  for (const id of selectedIds.value) {
    fileStore.updateCategory(id, cat)
  }
  ElMessage.success(`已将 ${selectedIds.value.size} 个文件分类为「${cat}」`)
  selectedIds.value.clear()
  batchCategory.value = ''
}

async function onBatchDelete() {
  const ids = [...selectedIds.value]
  let successCount = 0
  for (const id of ids) {
    try {
      await fileStore.deleteFile(id)
      successCount++
    } catch { /* individual failure — continue */ }
  }
  ElMessage.success(`已删除 ${successCount}/${ids.length} 个文件`)
  selectedIds.value.clear()
}

const allCategoriesForBatch = computed(() => {
  const all = new Set<string>()
  for (const f of fileStore.files) all.add(f.category)
  return ['案件文书', '证据材料', ...all].filter(Boolean)
})

function onUploadMatterChange() {
  showNewCategory.value = false
  if (pendingFile.value) {
    uploadCategory.value = fileStore.suggestCategory(pendingFile.value.name, uploadMatterId.value)
  } else {
    uploadCategory.value = '其他'
  }
}

function addCustomCategory() {
  const name = newCategoryName.value.trim()
  if (!name || !uploadMatterId.value) return
  matterStore.addCategory(uploadMatterId.value, name)
  uploadCategory.value = name
  showNewCategory.value = false
  newCategoryName.value = ''
}

function onFilePicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!fileStore.isAllowedFile(file.name)) {
    ElMessage.warning(`不支持的文件类型: ${file.name}，支持 PDF/Word/Excel/图片/文本等常见格式`)
    input.value = ''
    return
  }
  const reader = new FileReader()
  reader.onload = (ev) => {
    pendingFile.value = {
      name: file.name,
      data: ev.target?.result as string,
      type: file.type,
    }
    // Auto-suggest category
    if (uploadMatterId.value) {
      uploadCategory.value = fileStore.suggestCategory(file.name, uploadMatterId.value)
    }
  }
  reader.readAsDataURL(file)
}

async function confirmUpload() {
  if (!pendingFile.value || !uploadMatterId.value) return
  try {
    await fileStore.addFile(
      pendingFile.value.name,
      pendingFile.value.data,
      pendingFile.value.type,
      uploadCategory.value,
      uploadMatterId.value,
    )
    showUploadDialog.value = false
    pendingFile.value = null
    uploadMatterId.value = ''
    uploadCategory.value = '其他'
    ElMessage.success('文件上传成功')
  } catch (e) {
    ElMessage.error('文件上传失败，请重试')
  }
}

const ctxMenuItems = computed<ContextMenuItem[]>(() => {
  if (!ctxFile.value) return []
  const f = ctxFile.value
  const items: ContextMenuItem[] = [
    { label: '预览', icon: Edit, handler: () => openPreview(f) },
    { label: '下载', icon: Download, handler: downloadFile },
  ]
  if (/\.(md|txt|markdown)$/i.test(f.name)) {
    items.push({ label: '校对文书', icon: Search, handler: () => { openPreview(f); reviewCurrent() } })
  }
  // 文书类文件（md/txt）→ 一键转 Word，可交付/打印
  if (/\.(md|txt)$/i.test(f.name)) {
    items.push({ label: exportingDocx.value ? '导出 Word 中…' : '导出 Word (.docx)', icon: Document, handler: exportAsDocx })
  }
  items.push(
    { label: '', divider: true },
    { label: '删除', icon: Delete, danger: true, handler: () => { fileStore.deleteFile(f.id); ElMessage.success('文件已删除') } },
  )
  return items
})

// ── 导出 Word：调用后端 export_docx（Markdown → docx，宋体/黑体法律文书格式） ──
const exportingDocx = ref(false)

async function exportAsDocx() {
  const f = ctxFile.value
  if (!f || exportingDocx.value) return
  exportingDocx.value = true
  try {
    // 文件 data 是 Data URL（data:text/markdown;base64,...）
    const raw = atob((f.data.split(',')[1] || ''))
    const markdown = decodeURIComponent(raw.split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''))
    const matter = f.matterId ? matterStore.matters.find(m => m.id === f.matterId) : null
    await exportMarkdownAsDocx(f.name.replace(/\.(md|txt)$/i, ''), markdown, matter?.title || '')
    ElMessage.success('已导出 Word 文档')
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败（需要后端引擎运行）')
  } finally {
    exportingDocx.value = false
  }
}

function formatDate(d: Date) {
  return new Date(d).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.file-panel {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px 0;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.file-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── 校对结果 ── */
.review-list { display: flex; flex-direction: column; gap: 8px; max-height: 46vh; overflow-y: auto; }
.review-item { padding: 10px 12px; border-radius: var(--radius-sm); border: 1px solid var(--el-border-color-lighter); background: var(--el-fill-color-lighter); }
.review-item.sev-严重 { border-left: 3px solid var(--legal-danger); }
.review-item.sev-一般 { border-left: 3px solid var(--legal-warning); }
.review-item.sev-提示 { border-left: 3px solid var(--legal-text-muted); }

/* ── Tree panel (left) ── */
.file-tree-panel {
  width: 260px;
  min-width: 260px;
  border-right: 1px solid var(--el-border-color-lighter);
  padding: 0 8px 8px;
  overflow-y: auto;
  flex-shrink: 0;
}

.file-tree-search {
  padding: 0 4px 8px;
  position: sticky;
  top: 0;
  background: var(--legal-bg);
  z-index: 1;
}

.file-tree {
  font-size: 13px;
}

.file-tree :deep(.el-tree-node__content) {
  height: 34px;
  border-radius: var(--radius-sm);
}

.file-tree :deep(.el-tree-node__content:hover) {
  background: var(--el-fill-color-light);
}

.file-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: var(--el-color-primary-light-9);
  color: var(--legal-navy);
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.tree-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.tree-count {
  font-size: 11px;
  color: var(--legal-text-muted);
  margin-left: auto;
  padding: 0 4px;
}

.tree-ai-tag {
  font-size: 9px;
  background: var(--legal-gold-bg);
  color: var(--legal-gold-dark);
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
  margin-left: 4px;
}

/* ── File content (right) — split layout ── */
.file-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 16px 16px;
  overflow: hidden;
}
.file-content.has-preview .fc-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}
.file-content:not(.has-preview) .fc-list {
  overflow-y: auto;
  flex: 1;
}

.file-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.file-header h3 {
  margin: 0;
  font-size: 17px;
  font-family: var(--font-heading);
  color: var(--legal-navy);
}

.file-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}


.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: var(--legal-text-muted);
}

.empty-state p { margin: 12px 0 0; font-size: 14px; }

.file-list { display: flex; flex-direction: column; gap: 4px; }

.file-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  transition: box-shadow var(--transition-fast), background var(--transition-fast);
}

.file-row:hover { box-shadow: var(--shadow-sm); }
.file-row.is-selected { background: var(--el-color-primary-light-9); border-color: var(--el-color-primary-light-7); }

.file-checkbox {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding-right: 2px;
}

.file-click-area {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.file-icon {
  flex-shrink: 0;
  width: 36px; height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--legal-navy-bg);
  border-radius: var(--radius-sm);
}

.file-info { flex: 1; min-width: 0; }

.file-name {
  font-weight: 500; font-size: 13px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.file-meta {
  display: flex; gap: 8px; align-items: center;
  font-size: 12px; color: var(--legal-text-muted); margin-top: 2px;
}

.file-ops {
  display: flex; align-items: center; gap: 4px; flex-shrink: 0;
}

.pending-file-name { margin-left: 8px; font-size: 13px; color: var(--legal-text-secondary); }

.category-row { display: flex; gap: 4px; align-items: center; }

.new-category-row {
  display: flex; gap: 6px; margin-top: 8px;
}

/* ── Batch action bar ── */
.batch-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 8px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: var(--radius-md);
  animation: batchSlideIn 0.2s ease-out;
}

@keyframes batchSlideIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.batch-info {
  font-size: 13px;
  font-weight: 600;
  color: var(--legal-navy);
  margin-right: 4px;
  white-space: nowrap;
}

/* ── Drop zone overlay ── */
.drop-zone {
  position: absolute;
  inset: 0;
  z-index: 100;
  background: var(--legal-navy-bg);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
}

.drop-zone-content {
  background: var(--legal-bg-card);
  border: 2px dashed var(--legal-navy);
  border-radius: var(--radius-xl);
  padding: 40px 60px;
  text-align: center;
  color: var(--legal-navy);
  box-shadow: var(--shadow-lg);
}

.drop-zone-content p {
  margin: 12px 0 0;
  font-size: 16px;
  font-weight: 600;
}

.drop-fade-enter-active, .drop-fade-leave-active {
  transition: opacity 0.2s ease;
}
.drop-fade-enter-from, .drop-fade-leave-to {
  opacity: 0;
}

/* ── File type icon colors ── */
.file-type-image { background: var(--file-type-image-bg); color: var(--file-type-image-color); }
.file-type-pdf { background: var(--file-type-pdf-bg); color: var(--file-type-pdf-color); }
.file-type-doc { background: var(--file-type-doc-bg); color: var(--file-type-doc-color); }
.file-type-sheet { background: var(--file-type-sheet-bg); color: var(--file-type-sheet-color); }

/* ── Case-grouped file view ── */
.file-group-by-case {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fg-case-group {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-md);
  background: var(--legal-bg-card);
  overflow: hidden;
}

.fg-case-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  color: var(--legal-navy);
}

.fg-case-title {
  font-weight: var(--weight-semibold);
  font-size: 14px;
  flex: 1;
}

.fg-case-count {
  font-size: 12px;
  color: var(--legal-text-muted);
}

.fg-case-group .file-list {
  padding: 4px;
  gap: 2px;
}

.fg-case-group .file-row {
  border: none;
  border-radius: 0;
  padding: 6px 10px;
}

.fg-case-group .file-row:not(:last-child) {
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.fg-case-group .file-row:hover {
  background: var(--el-fill-color-light);
  box-shadow: none;
}



/* ── Inline preview / editor panel (fc-preview) ── */
.fc-preview {
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 8px;
  background: var(--legal-bg-card);
  display: flex;
  flex-direction: column;
  min-height: 240px;
  max-height: 50vh;
  overflow: hidden;
  border-radius: var(--radius-md);
  border: 1px solid var(--el-border-color-lighter);
}

.fcp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-lighter);
  flex-shrink: 0;
}

.fcp-name {
  font-size: 13px;
  font-weight: var(--weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.fcp-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 8px;
}

.fcp-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px 20px;
  overflow: auto;
}

.fcp-image {
  max-width: 100%;
  max-height: 40vh;
  object-fit: contain;
  border-radius: var(--radius-sm);
}

.fcp-editor {
  width: 100%;
  min-height: 200px;
  max-height: 40vh;
  border: 1px solid var(--el-border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
  font-family: var(--font-ui);
  font-size: 14px;
  line-height: 1.7;
  resize: vertical;
  background: var(--legal-bg-card);
  color: var(--legal-text);
  outline: none;
}
.fcp-editor:focus {
  border-color: var(--legal-navy);
  box-shadow: 0 0 0 1px var(--legal-navy) inset;
}

.fcp-markdown {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.7;
  cursor: text;
  padding: 4px;
}

.fcp-markdown :deep(h1) { font-size: 22px; margin: 0 0 12px; color: var(--legal-navy); }
.fcp-markdown :deep(h2) { font-size: 18px; margin: 16px 0 8px; color: var(--legal-navy); }
.fcp-markdown :deep(h3) { font-size: 15px; margin: 12px 0 6px; color: var(--legal-navy); }
.fcp-markdown :deep(p) { margin: 0 0 8px; }
.fcp-markdown :deep(ul), .fcp-markdown :deep(ol) { padding-left: 20px; margin: 4px 0; }
.fcp-markdown :deep(code) { background: var(--el-fill-color); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
.fcp-markdown :deep(blockquote) { border-left: 3px solid var(--legal-gold); margin: 8px 0; padding: 4px 12px; color: var(--legal-text-secondary); background: var(--el-fill-color-lighter); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
.fcp-markdown :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
.fcp-markdown :deep(th), .fcp-markdown :deep(td) { border: 1px solid var(--el-border-color); padding: 6px 10px; text-align: left; }
.fcp-markdown :deep(th) { background: var(--el-fill-color); font-weight: 600; }

.fcp-placeholder { text-align: center; color: var(--legal-text-muted); padding: 20px 0; }
.fcp-placeholder .fcp-name { font-size: 15px; font-weight: 600; color: var(--legal-text); margin: 8px 0 4px; }
.fcp-placeholder .fcp-meta { font-size: 13px; margin: 0 0 8px; }
.fcp-placeholder .fcp-hint { font-size: 12px; margin: 0; }
/* ── 文档抽取：AI可读徽章 + 解析文本预览 ── */
.parsed-tag { --el-tag-bg-color: var(--legal-success, #2d7d4e); }
.pdf-text-preview {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--legal-text);
  background: var(--el-fill-color-light);
  border-radius: var(--radius-sm);
  padding: 12px;
  margin: 0;
  max-height: 60vh;
  overflow-y: auto;
}

.fcp-office-tag {
  font-size: 10px !important;
  height: 20px;
  line-height: 18px;
}


/* ── Tree panel adjustments ── */
.file-stat {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  font-size: 13px;
  transition: all var(--transition-fast);
}

.file-stat:hover, .file-stat.active {
  border-color: var(--legal-navy);
  background: var(--el-color-primary-light-9);
}

.stat-num { font-weight: var(--weight-bold); color: var(--legal-navy); font-size: 15px; }
.stat-label { color: var(--legal-text-secondary); }

.stat-del {
  margin-left: 2px;
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--transition-fast);
  flex-shrink: 0;
}
.file-stat:hover .stat-del { opacity: 0.6; }
.file-stat:hover .stat-del:hover { opacity: 1; }

.fc-summary {
  font-size: 12px;
  color: var(--legal-text-muted);
  margin-bottom: 8px;
  padding: 0 4px;
}

</style>
