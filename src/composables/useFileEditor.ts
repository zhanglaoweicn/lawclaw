/**
 * 文件编辑复合函数
 *
 * 统一管理文件的编辑、保存逻辑，避免 ChatPanel / CaseDetailView / FilePanel 三处重复。
 * 使用方式：
 *   const editor = useFileEditor(fileStore, () => ElMessage.success('已保存'))
 */
import { ref, type Ref } from 'vue'
import type { ManagedFile } from '../types/legal'
import { dataUrlToText, textToDataUrl } from '../lib/encoding'

export interface EditableFile {
  /** 对应 IndexedDB 记录 id（按 id 定位可避免同内容文件错改） */
  id?: string
  name: string
  data: string
  size: number
  type: string
}

export function useFileEditor(
  fileStore: { files: ManagedFile[]; addFile: Function; deleteFile: Function },
  onSaveSuccess?: () => void,
  onSaveError?: () => void,
) {
  const editing = ref(false)
  const editText = ref('')
  const saving = ref(false)

  function startEditing(file: EditableFile) {
    if (!isTextFile(file.name)) return
    const raw = dataUrlToText(file.data)
    if (!raw && file.size > 4) {
      console.warn('Failed to decode file for editing:', file.name)
      return
    }
    editText.value = raw
    editing.value = true
  }

  function cancelEditing() {
    editing.value = false
    editText.value = ''
  }

  async function saveEdits(file: Ref<EditableFile | null>) {
    if (!file.value) return
    saving.value = true
    try {
      // UTF-8 安全编码（btoa 直编码中文会抛异常/写坏数据）；允许保存空内容
      const dataUrl = textToDataUrl(editText.value, 'text/markdown')
      // 优先按 id 定位记录（旧版按 base64 data 全等定位：两个内容相同的文件会错改到
      // 另一条记录）；再经 updateFile 原地写回——旧版「先删后写」在 add 失败时
      // 旧记录已被删，文件数据永久丢失
      const fileRecord = fileStore.files.find((f: ManagedFile) =>
        file.value!.id ? f.id === file.value!.id : f.data === file.value!.data,
      )
      if (fileRecord) {
        fileRecord.data = dataUrl
        fileRecord.size = dataUrl.length
        const mod = await import('../lib/db')
        await mod.updateFile(fileRecord.id, { data: dataUrl, size: dataUrl.length })
      }
      file.value.data = dataUrl
      file.value.size = dataUrl.length
      editing.value = false
      onSaveSuccess?.()
    } catch {
      onSaveError?.()
    } finally {
      saving.value = false
    }
  }

  function isTextFile(name: string) {
    return /\.(md|txt|markdown|json|xml|yaml|yml|csv|ts|js|vue)$/i.test(name)
  }

  function isImageFile(name: string) {
    return /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(name)
  }

  return { editing, editText, saving, startEditing, cancelEditing, saveEdits, isTextFile, isImageFile }
}
