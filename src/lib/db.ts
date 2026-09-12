const DB_NAME = 'LawClaw'
const DB_VERSION = 2
const FILES_STORE = 'files'
const TIMELINE_STORE = 'timeline'

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(FILES_STORE)) {
        const store = db.createObjectStore(FILES_STORE, { keyPath: 'id' })
        store.createIndex('matterId', 'matterId', { unique: false })
        store.createIndex('category', 'category', { unique: false })
      }
      if (!db.objectStoreNames.contains(TIMELINE_STORE)) {
        const store = db.createObjectStore(TIMELINE_STORE, { keyPath: 'id' })
        store.createIndex('matterId', 'matterId', { unique: false })
        store.createIndex('type', 'type', { unique: false })
        store.createIndex('createdAt', 'createdAt', { unique: false })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export interface FileRecord {
  id: string
  name: string
  size: number
  type: string
  category: string
  matterId: string
  createdAt: string
  data: string
  extractedText?: string
  extractor?: string
}

export async function getAllFiles(): Promise<FileRecord[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(FILES_STORE, 'readonly')
    const store = tx.objectStore(FILES_STORE)
    const req = store.getAll()
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export async function addFile(record: FileRecord): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(FILES_STORE, 'readwrite')
    const store = tx.objectStore(FILES_STORE)
    store.add(record)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function deleteFile(id: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(FILES_STORE, 'readwrite')
    const store = tx.objectStore(FILES_STORE)
    store.delete(id)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function updateFile(id: string, patch: Partial<FileRecord>): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(FILES_STORE, 'readwrite')
    const store = tx.objectStore(FILES_STORE)
    const getReq = store.get(id)
    getReq.onsuccess = () => {
      const rec = getReq.result
      if (!rec) { resolve(); return }
      store.put({ ...rec, ...patch })
    }
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function updateFileCategory(id: string, category: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(FILES_STORE, 'readwrite')
    const store = tx.objectStore(FILES_STORE)
    const req = store.get(id)
    req.onsuccess = () => {
      const record = req.result
      if (record) {
        record.category = category
        store.put(record)
      }
      tx.oncomplete = () => resolve()
    }
    req.onerror = () => reject(req.error)
  })
}

export async function getFilesByMatter(matterId: string): Promise<FileRecord[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(FILES_STORE, 'readonly')
    const store = tx.objectStore(FILES_STORE)
    const index = store.index('matterId')
    const req = index.getAll(matterId)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export interface TimelineRecord {
  id: string
  matterId: string
  type: string
  title: string
  description?: string
  createdAt: string
  createdBy?: string
  metadata?: string
}

export async function addTimelineEvent(record: TimelineRecord): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(TIMELINE_STORE, 'readwrite')
    const store = tx.objectStore(TIMELINE_STORE)
    store.add(record)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function getTimelineEvents(matterId: string): Promise<TimelineRecord[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(TIMELINE_STORE, 'readonly')
    const store = tx.objectStore(TIMELINE_STORE)
    const index = store.index('matterId')
    const req = index.getAll(matterId)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/** 全库时间轴事件（经验记忆召回用：跨案件决策/里程碑检索） */
export async function getAllTimelineEvents(): Promise<TimelineRecord[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(TIMELINE_STORE, 'readonly')
    const store = tx.objectStore(TIMELINE_STORE)
    const req = store.getAll()
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export async function deleteTimelineEvent(id: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(TIMELINE_STORE, 'readwrite')
    const store = tx.objectStore(TIMELINE_STORE)
    store.delete(id)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function deleteTimelineEventsByMatter(matterId: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(TIMELINE_STORE, 'readwrite')
    const store = tx.objectStore(TIMELINE_STORE)
    const index = store.index('matterId')
    const req = index.openCursor(matterId)
    req.onsuccess = () => {
      const cursor = req.result
      if (cursor) {
        store.delete(cursor.primaryKey)
        cursor.continue()
      } else {
        tx.oncomplete = () => resolve()
      }
    }
    req.onerror = () => reject(req.error)
  })
}
