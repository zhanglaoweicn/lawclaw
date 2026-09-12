import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ManagedFile, FileCategory } from '../types/legal'
import * as db from '../lib/db'

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

const DEFAULT_CATEGORIES: FileCategory[] = ['案件文书', '证据材料', '其他']

const ALLOWED_FILE_EXTENSIONS = [
  'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
  'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg',
  'txt', 'md', 'csv', 'json', 'xml', 'yaml', 'yml',
  'wps', 'ofd',
]

function isAllowedFile(name: string): boolean {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return ALLOWED_FILE_EXTENSIONS.includes(ext)
}

// Smart category suggestion based on filename patterns
const FILENAME_CATEGORY_RULES: [RegExp, string][] = [
  [/起诉|上诉|答辩|代理词|辩护|申请书|异议书/i, '案件文书'],
  [/证据|清单|明细|转账|流水|聊天|合同|借条|收据|发票/i, '证据材料'],
  [/判决|裁定|传票|通知|决定书|调解书/i, '法院文书'],
  [/身份|证照|执照|登记|许可|资质/i, '主体资格'],
  [/鉴定|评估|报告|审计|检验/i, '鉴定评估'],
  [/协议|合约|备忘录/i, '合同文件'],
  [/照片|截图|录像|录音|影像/i, '视听资料'],
]

function suggestCategory(fileName: string, matterId?: string): string {
  for (const [pattern, category] of FILENAME_CATEGORY_RULES) {
    if (pattern.test(fileName)) return category
  }
  return '其他'
}

export const useFileStore = defineStore('file', () => {
  const files = ref<ManagedFile[]>([])
  const loaded = ref(false)
  const loading = ref(false)

  async function load() {
    if (loaded.value || loading.value) return
    loading.value = true
    try {
      const records = await db.getAllFiles()
      files.value = records.map(r => ({
        ...r,
        createdAt: new Date(r.createdAt),
      }))
      loaded.value = true
    } catch (e) {
      console.warn('IndexedDB 加载文件失败:', e)
    } finally {
      loading.value = false
    }
  }

  function filesByCategory(cat: FileCategory): ManagedFile[] {
    return files.value.filter(f => f.category === cat)
  }

  function filesByMatter(matterId: string): ManagedFile[] {
    return files.value.filter(f => f.matterId === matterId)
  }

  async function addFile(name: string, data: string, type: string, category: FileCategory, matterId: string): Promise<ManagedFile> {
    const now = new Date()
    // Calculate original file size from base64 Data URL
    const rawData = data.split(',')[1] || ''
    const originalSize = Math.round((rawData.length * 3) / 4)
    const f: ManagedFile = {
      id: generateId(), name, size: originalSize, type, category, matterId,
      createdAt: now, data,
    }
    try {
      await db.addFile({ ...f, createdAt: now.toISOString() })
      files.value.unshift(f)
      // 上传即解析：后端抽取适配层生成全文文本（全文搜索/AI 知识库的数据入口）
      void parseAndStoreExtracted(f)
      // Auto-create timeline event for file upload
      import('./timeline').then(({ useTimelineStore }) => {
        const tl = useTimelineStore()
        if (!tl.events.some(e => e.matterId === matterId && e.type === 'file_upload' && e.title.includes(name))) {
          tl.addEvent({
            matterId,
            type: 'file_upload',
            title: `文件上传: ${name}`,
            createdBy: 'user',
          })
        }
      })
    } catch (e) {
      console.error('IndexedDB 写入失败，文件未保存:', e)
      throw e // Re-throw so caller knows it failed
    }
    return f
  }

  /** 上传后异步调用后端解析适配层，抽取全文并入库（全文搜索 / AI 知识库的数据入口） */
  async function parseAndStoreExtracted(f: ManagedFile) {
    try {
      const { backend } = await import('../lib/backend')
      const raw = f.data.split(',')[1] || ''
      if (!raw) return
      const r = await backend.parseDocument(f.name, raw)
      if (r?.ok && r.text && r.text.length > 30) {
        f.extractedText = r.text
        f.extractor = r.extractor
        await db.updateFile(f.id, { extractedText: r.text, extractor: r.extractor })
      }
    } catch {
      // 后端未连接/解析失败 → 文件仍可管理，只是无全文
    }
  }

  async function deleteFile(id: string) {
    try {
      await db.deleteFile(id)
      files.value = files.value.filter(f => f.id !== id)
    } catch (e) {
      console.error('IndexedDB 删除失败:', e)
      throw e
    }
  }

  async function updateCategory(id: string, category: FileCategory) {
    const f = files.value.find(x => x.id === id)
    if (!f) return
    const prevCategory = f.category
    f.category = category
    try {
      await db.updateFileCategory(id, category)
    } catch (e) {
      f.category = prevCategory // roll back
      console.error('IndexedDB 更新分类失败:', e)
    }
  }

  async function deleteFilesByMatter(matterId: string) {
    const toDelete = files.value.filter(f => f.matterId === matterId)
    if (toDelete.length === 0) return
    // Remove from memory first
    files.value = files.value.filter(f => f.matterId !== matterId)
    // Then delete from IndexedDB one by one (catch each failure individually)
    for (const f of toDelete) {
      try { await db.deleteFile(f.id) } catch (e) { console.warn('IndexedDB 删除文件失败:', f.id, e) }
    }
  }

  load()

  return { files, loaded, loading, filesByCategory, filesByMatter, addFile, deleteFile, updateCategory, deleteFilesByMatter, isAllowedFile, suggestCategory, DEFAULT_CATEGORIES }
})
