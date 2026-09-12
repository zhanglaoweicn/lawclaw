import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useMatterStore } from './matter'
import type { CaseSubView } from '../types/legal'

export const useCaseViewStore = defineStore('caseView', () => {
  const subView = ref<CaseSubView>('list')
  const selectedMatterId = ref<string | null>(null)
  const searchQuery = ref('')
  const filterStage = ref<string | null>(null)
  const filterPracticeArea = ref<string | null>(null)
  const showNewCaseDialogFlag = ref(0) // increment to signal

  const matterStore = useMatterStore()

  const selectedMatter = computed(() => {
    if (!selectedMatterId.value) return null
    return matterStore.matters.find(m => m.id === selectedMatterId.value) || null
  })

  function showCaseList() {
    subView.value = 'list'
    selectedMatterId.value = null
  }

  function showCaseDetail(matterId: string) {
    selectedMatterId.value = matterId
    subView.value = 'detail'
  }

  function setFilterStage(stage: string | null) {
    filterStage.value = stage
  }

  function setFilterPracticeArea(area: string | null) {
    filterPracticeArea.value = area
  }

  function setSearchQuery(query: string) {
    searchQuery.value = query
  }

  function triggerNewCaseDialog() {
    showNewCaseDialogFlag.value++
  }

  function resetFilters() {
    filterStage.value = null
    filterPracticeArea.value = null
    searchQuery.value = ''
  }

  return {
    subView, selectedMatterId, searchQuery, filterStage, filterPracticeArea,
    selectedMatter,
    showCaseList, showCaseDetail, setFilterStage, setFilterPracticeArea,
    setSearchQuery, resetFilters,
    showNewCaseDialogFlag, triggerNewCaseDialog,
  }
})
