<template>
  <div class="library-view">
    <header class="view-header">
      <div class="header-main">
        <h1 class="text-huge">资料库</h1>
        <div class="header-actions">
          <n-button quaternary circle @click="handleRefresh" title="刷新列表">
            <template #icon><n-icon :component="RefreshOutline" /></template>
          </n-button>
          
          <n-button tertiary round class="sp-secondary-btn" @click="handleEnrich">
            <template #icon><n-icon :component="FlashOutline" /></template>
            标签补全
          </n-button>
          
          <n-button tertiary round class="sp-secondary-btn" @click="handleScan">
             <template #icon><n-icon :component="ScanCircleOutline" /></template>
            全盘扫描
          </n-button>

          <div class="header-pagination-container" v-if="libraryStore.totalSongs > libraryStore.pageSize">
            <n-pagination
              v-model:page="libraryStore.currentPage"
              :page-count="Math.ceil(libraryStore.totalSongs / libraryStore.pageSize)"
              @update:page="(page: number) => libraryStore.fetchLocalSongs(page)"
              simple
            />
          </div>
        </div>
      </div>
    </header>

    <div class="view-content">
      <div class="list-wrapper">
        <SongList 
          :history="libraryStore.songs"
          :loading="libraryStore.isLoading"
          @play="handlePlay"
          @toggleFavorite="libraryStore.toggleFavorite"
          @repair="handleOpenMatcher"
          @delete="handleDelete"
          @redownload="handleRedownload"
        />
      </div>
      
      <div class="pagination-wrapper footer-pagination" v-if="libraryStore.totalSongs > libraryStore.pageSize">
        <n-pagination
          v-model:page="libraryStore.currentPage"
          :page-count="Math.ceil(libraryStore.totalSongs / libraryStore.pageSize)"
          @update:page="(page: number) => libraryStore.fetchLocalSongs(page)"
          simple
        />
      </div>

      <div v-if="!libraryStore.isLoading && libraryStore.songs.length === 0" class="empty-state">
        <n-empty description="资料库内容为空，点击上方扫描按钮查找本地音乐">
           <template #icon>
              <n-icon size="48" :component="LibraryOutline" color="var(--text-tertiary)" />
           </template>
        </n-empty>
      </div>
      
      <MetadataMatcher 
        v-model:show="showMatcher" 
        :song="matcherTarget" 
        :mode="matcherMode"
        @success="handleMatcherSuccess"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 桌面端资料库视图 - Spotify 风格
 */
import { onMounted, ref, watch } from 'vue'
import { NPagination, NButton, NIcon, NEmpty, useMessage, useDialog } from 'naive-ui'
import { RefreshOutline, LibraryOutline, FlashOutline, ScanCircleOutline } from '@vicons/ionicons5'
import { useLibraryStore } from '@/stores/library'
import { usePlayerStore } from '@/stores/player'
import * as libraryApi from '@/api/library'
import SongList from '@/components/SongList.vue'
import MetadataMatcher from '@/components/library/MetadataMatcher.vue'

const message = useMessage()
const dialog = useDialog()
const libraryStore = useLibraryStore()
const playerStore = usePlayerStore()

const props = defineProps({
  history: { type: Array as () => any[], default: () => [] },
  loading: { type: Boolean, default: false },
  selectedArtistName: { type: String, default: null },
  mode: { type: String, default: 'library' }
})

const showMatcher = ref(false)
const matcherTarget = ref<any>(null)
const matcherMode = ref<'metadata' | 'download'>('metadata')

const emit = defineEmits(['play', 'repair', 'toggleFavorite', 'delete', 'redownload'])

const handlePlay = (song: any) => {
  playerStore.setPlaylist(libraryStore.songs)
  playerStore.playSong(song)
}

const handleDelete = async (song: any) => {
    dialog.warning({
        title: '确认删除',
        content: `确认删除 "${song.title}" 吗？此操作无法撤销。`,
        positiveText: '确认删除',
        negativeText: '取消',
        onPositiveClick: async () => {
             const success = await libraryStore.deleteSong(song) 
             if (success) message.success('删除成功')
        }
    })
}

const handleRedownload = async (song: any) => {
    matcherTarget.value = song
    matcherMode.value = 'download'
    showMatcher.value = true
}

const handleOpenMatcher = (song: any) => {
    matcherTarget.value = song
    matcherMode.value = 'metadata'
    showMatcher.value = true
}

const handleMatcherSuccess = () => {
    // Refresh list to show new metadata
    libraryStore.fetchLocalSongs(libraryStore.currentPage)
}

const handleRefresh = async () => {
  await libraryStore.fetchLocalSongs(libraryStore.currentPage)
  message.success('本地列表已刷新')
}

const handleScan = async () => {
  try {
    message.loading('正在全盘扫描本地文件...')
    const res = await libraryApi.scanLibrary()
    let msg = `扫描完成，发现 ${res.new_files_found} 个新文件`
    if (res.removed_files_count > 0) {
        msg += `，并清理了 ${res.removed_files_count} 个失效记录`
    }
    message.success(msg)
    await libraryStore.fetchLocalSongs(1)
  } catch {
    message.error('扫描失败')
  }
}

const handleEnrich = async () => {
    try {
        message.loading('正在触发后台标签补全任务...')
        const res = await libraryApi.enrichLocalFiles()
        if (res.success) {
             message.success(res.message || '补全任务已启动')
             // 刷新列表以查看可能的早期结果
             setTimeout(() => libraryStore.fetchLocalSongs(1), 2000)
        } else {
             message.error('任务启动异常')
        }
    } catch {
        message.error('整理失败')
    }
}

onMounted(() => {
  libraryStore.fetchLocalSongs(1)
})
</script>

<style scoped>
.library-view {
  padding-bottom: 32px;
}

.view-header {
  margin-bottom: 24px;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.sp-secondary-btn {
  font-weight: 700;
  border-color: #727272;
  color: #fff;
}

.sp-secondary-btn:hover {
  border-color: #fff;
  transform: scale(1.02);
}

.list-wrapper {
  margin-top: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

.empty-state {
  padding: 120px 0;
  display: flex;
  justify-content: center;
}
</style>
