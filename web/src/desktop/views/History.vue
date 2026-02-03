<template>
  <div class="history-view">
    <header class="view-header">
      <div class="header-main">
        <div class="header-info">
          <h1 class="text-huge">最近播放</h1>
          <p class="subtitle">您最近听过的所有曲目</p>
        </div>
        
        <div class="header-pagination-container" v-if="libraryStore.totalHistorySongs > libraryStore.pageSize">
          <n-pagination
            v-model:page="libraryStore.currentHistoryPage"
            :page-count="Math.ceil(libraryStore.totalHistorySongs / libraryStore.pageSize)"
            @update:page="(page: number) => libraryStore.fetchHistory(page)"
            simple
          />
        </div>
      </div>
    </header>

    <main class="view-content">
      <div class="history-content">
        <SongList 
          :history="libraryStore.historySongs" 
          :loading="isLoading"
          mode="history"
          :sort-field="libraryStore.sortField"
          :sort-order="libraryStore.sortOrder"
          @play="handlePlay" 
          @toggleFavorite="libraryStore.toggleFavorite"
          @sort="({ field, order }) => { libraryStore.sortField = field; libraryStore.sortOrder = order; libraryStore.fetchHistory(1); }"
        />

        <div class="footer-pagination" v-if="libraryStore.totalHistorySongs > libraryStore.pageSize">
          <n-pagination
            v-model:page="libraryStore.currentHistoryPage"
            :page-count="Math.ceil(libraryStore.totalHistorySongs / libraryStore.pageSize)"
            @update:page="(page: number) => libraryStore.fetchHistory(page)"
            simple
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
/**
 * 桌面端历史记录视图 - Spotify 风格
 */
import { ref, onMounted } from 'vue'
import { NSpin, NEmpty, NIcon, NPagination } from 'naive-ui'
import { TimeOutline } from '@vicons/ionicons5'
import { useLibraryStore, usePlayerStore } from '@/stores'
import SongList from '@/components/SongList.vue'

const libraryStore = useLibraryStore()
const playerStore = usePlayerStore()
const isLoading = ref(false)

const handlePlay = (song: any) => {
  playerStore.playSong(song)
}

onMounted(async () => {
    isLoading.value = true
    await libraryStore.fetchHistory()
    isLoading.value = false
})
</script>

<style scoped>
.history-view {
  padding-bottom: 32px;
}

.view-header {
  margin-bottom: 24px;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin-top: 4px;
}

.history-content {
  margin-top: 16px;
}

.footer-pagination {
    display: flex;
    justify-content: center;
    margin-top: 32px;
}

.empty-state {
  padding: 120px 0;
  display: flex;
  justify-content: center;
  color: var(--text-tertiary);
}
</style>
