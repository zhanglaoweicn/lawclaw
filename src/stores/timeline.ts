import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TimelineEvent } from '../types/legal'
import * as db from '../lib/db'

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

export const useTimelineStore = defineStore('timeline', () => {
  const events = ref<TimelineEvent[]>([])
  const loaded = ref(false)
  /** 全量加载完成标记（loadEventsForMatter 只覆盖单案视图，不算全量） */
  const allLoaded = ref(false)

  /** 加载全部案件的时间轴事件（经验记忆召回的语料；不覆盖已加载的当前案件视图） */
  async function loadAllEvents() {
    if (allLoaded.value) return
    try {
      const records = await db.getAllTimelineEvents()
      const mapped = records.map(r => ({
        ...r,
        type: r.type as TimelineEvent['type'],
        createdBy: r.createdBy as TimelineEvent['createdBy'],
        createdAt: new Date(r.createdAt),
        metadata: r.metadata ? JSON.parse(r.metadata) : undefined,
      }))
      events.value = mapped
      loaded.value = true
      allLoaded.value = true
    } catch (e) {
      console.warn('加载全量时间轴失败:', e)
    }
  }

  async function loadEventsForMatter(matterId: string) {
    try {
      const records = await db.getTimelineEvents(matterId)
      events.value = records.map(r => ({
        ...r,
        type: r.type as TimelineEvent['type'],
        createdBy: r.createdBy as TimelineEvent['createdBy'],
        createdAt: new Date(r.createdAt),
        metadata: r.metadata ? JSON.parse(r.metadata) : undefined,
      }))
      loaded.value = true
    } catch (e) {
      console.warn('加载时间轴事件失败:', e)
      events.value = []
    }
  }

  async function addEvent(event: Omit<TimelineEvent, 'id' | 'createdAt'>, customTime?: Date): Promise<TimelineEvent> {
    // Basic dedup: skip if same type + title within last 5 seconds
    const recent = events.value[0]
    if (recent && recent.type === event.type && recent.title === event.title &&
        (Date.now() - recent.createdAt.getTime()) < 5000) {
      return recent
    }
    const now = customTime || new Date()
    const ev: TimelineEvent = {
      ...event,
      id: generateId(),
      createdAt: now,
    }
    try {
      await db.addTimelineEvent({
        id: ev.id,
        matterId: ev.matterId,
        type: ev.type,
        title: ev.title,
        description: ev.description,
        createdAt: now.toISOString(),
        createdBy: ev.createdBy,
        metadata: ev.metadata ? JSON.stringify(ev.metadata) : undefined,
      })
    } catch (e) {
      console.warn('IndexedDB 写入时间轴事件失败:', e)
    }
    events.value.unshift(ev)
    return ev
  }

  async function deleteEvent(id: string) {
    try {
      await db.deleteTimelineEvent(id)
    } catch (e) {
      console.warn('IndexedDB 删除时间轴事件失败:', e)
    }
    events.value = events.value.filter(e => e.id !== id)
  }

  async function clearMatterEvents(matterId: string) {
    try {
      await db.deleteTimelineEventsByMatter(matterId)
    } catch (e) {
      console.warn('IndexedDB 清除时间轴事件失败:', e)
    }
    events.value = events.value.filter(e => e.matterId !== matterId)
  }

  async function addSessionEvent(matterId: string, sessionTitle: string) {
    return addEvent({
      matterId,
      type: 'session',
      title: `AI 对话: ${sessionTitle}`,
      createdBy: 'user',
    })
  }

  return {
    events, loaded,
    loadEventsForMatter, loadAllEvents, addEvent, deleteEvent, clearMatterEvents,
    addSessionEvent,
  }
})
