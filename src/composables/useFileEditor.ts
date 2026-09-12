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
    if (!file.value || !editText.value) return
    saving.value = true
    try {
      // UTF-8 安全编码（btoa 直编码中文会抛异常/写坏数据）
      const dataUrl = textToDataUrl(editText.value, 'text/markdown')
      const fileRecord = fileStore.files.find((f: ManagedFile) => f.data === file.value!.data)
      if (fileRecord) {
        fileRecord.data = dataUrl
        fileRecord.size = dataUrl.length
        // Persist to IndexedDB: delete old record first, then add the updated one.
        // Delete-first prevents data duplication if the add succeeds but delete fails.
        const mod = await import('../lib/db')
        await mod.deleteFile(fileRecord.id)
        await mod.addFile({ ...fileRecord, createdAt: fileRecord.createdAt.toISOString() })
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
