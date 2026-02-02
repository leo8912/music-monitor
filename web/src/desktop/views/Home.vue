<script setup lang="ts">
/**
 * 桌面端主页视图 - Spotify 风格
 */

import { ref, onMounted, computed } from 'vue'
import { useMessage, NSpin, NIcon, NButton, NPagination } from 'naive-ui'
import { usePlayerStore, useLibraryStore, useSettingsStore } from '@/stores'
import { SettingsOutline } from '@vicons/ionicons5'


// 组件
import ArtistGrid from '@/components/ArtistGrid.vue'
import SongList from '@/components/SongList.vue'
import GlobalSearch from '@/components/GlobalSearch.vue'

const message = useMessage()
const playerStore = usePlayerStore()
const libraryStore = useLibraryStore()
const settingsStore = useSettingsStore()

// 时间问候语
const greeting = computed(() => {
    const hour = new Date().getHours()
    if (hour < 5) return '晚上好'
    if (hour < 11) return '早上好'
    if (hour < 13) return '中午好'
    if (hour < 18) return '下午好'
    return '晚上好'
})

// 处理播放
const handlePlay = (song: any) => {
  playerStore.setPlaylist(libraryStore.songs)
  playerStore.playSong(song)
}

// 初始化
onMounted(async () => {
    await libraryStore.fetchArtists()
    await libraryStore.fetchSongs()
})
// 刷新数据
const handleRefresh = async () => {
    await Promise.all([
        libraryStore.fetchArtists(),
        libraryStore.fetchSongs()
    ])
}

// 处理排序
const handleSort = async (field: string) => {
    if (libraryStore.sortField === field) {
        // 切换方向
        libraryStore.sortOrder = libraryStore.sortOrder === 'desc' ? 'asc' : 'desc'
    } else {
        libraryStore.sortField = field
        libraryStore.sortOrder = 'desc' // 切换字段时默认降序
    }
    await libraryStore.fetchSongs(1) // 排序后回到第一页
    message.success(`已按${field === 'title' ? '标题' : '发布时间'}${libraryStore.sortOrder === 'desc' ? '降序' : '升序'}排列`)
}
</script>

<template>
  <div class="home-view">
    <!-- Spotify 顶部渐变 -->
    <div class="home-gradient-bg"></div>

    <!-- 顶部欢迎区 (包含搜索栏) -->
    <header class="view-header">
      <div class="header-left">
          <h1 class="text-greeting">{{ greeting }}</h1>
      </div>
      
      <div class="header-center">
          <GlobalSearch @added="handleRefresh" />
      </div>

      <div class="header-right">
          <!-- TODO: Profile Icon or Settings -->
      </div>
    </header>

    <div class="view-content">
      <!-- 监控歌手区 -->
      <section class="sp-section artist-section">
        <div class="section-header">
          <h2 class="text-title">您的艺人</h2>
        </div>
        
        <ArtistGrid 
            :artists="libraryStore.mergedArtists"
            :selected-artist-name="libraryStore.selectedArtist?.name"
            :loading="libraryStore.isLoading"
            :refreshing-artist-name="libraryStore.refreshingArtistName || ''"
            @select="libraryStore.selectArtist"
            @delete="libraryStore.deleteArtist"
            @update="libraryStore.refreshArtist"
          />
      </section>

      <!-- 最近动态区 -->
      <section class="sp-section feed-section">
        <div class="section-header">
          <h2 class="text-title">最新发布</h2>
          <div class="pagination-container" v-if="libraryStore.totalSongs > libraryStore.pageSize">
              <n-pagination 
                v-model:page="libraryStore.currentPage" 
                :page-count="Math.ceil(libraryStore.totalSongs / libraryStore.pageSize)" 
                @update:page="libraryStore.fetchSongs"
                simple
              />
          </div>
        </div>
        
        <SongList 
            :history="libraryStore.songs"
            :loading="libraryStore.isLoading"
            :sort-field="libraryStore.sortField"
            :sort-order="libraryStore.sortOrder"
            @play="handlePlay"
            @toggleFavorite="libraryStore.toggleFavorite"
            @sort="handleSort"
          />

        <!-- 底部翻页 -->
        <div class="section-footer" style="display: flex; justify-content: flex-end; margin-top: 16px;">
            <div class="footer-pagination-container" v-if="libraryStore.totalSongs > libraryStore.pageSize">
              <n-pagination 
                v-model:page="libraryStore.currentPage" 
                :page-count="Math.ceil(libraryStore.totalSongs / libraryStore.pageSize)" 
                @update:page="libraryStore.fetchSongs"
                simple
              />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.footer-pagination-container {
    display: flex;
    justify-content: center;
    width: 100%;
}

.home-view {
  padding: 24px 32px;
  max-width: 1400px;
  margin: 0 auto;
  position: relative;
  min-height: 100%;
}

.home-gradient-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 332px;
  background-image: linear-gradient(rgba(0,0,0,0.6) 0, #121212 100%), var(--sp-gradient-overlay);
  background-color: rgb(83, 83, 83); /* 默认/fallback */
  z-index: 0;
  pointer-events: none;
  opacity: 0.6;
}

.view-header {
  position: relative;
  z-index: 100; /* High z-index to ensure dropdowns act above content */
  margin-bottom: 32px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start; /* top align */
  height: 48px;
}

.header-left { flex: 1; display: flex; align-items: center; height: 100%; }
.header-right { flex: 1; display: flex; justify-content: flex-end; height: 100%; }

/* Center Search */
.header-center {
    flex: 0 0 auto;
    display: flex;
    justify-content: center;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    top: 0;
}

.text-greeting {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -1px;
}

.sp-section {
  position: relative;
  z-index: 1;
  margin-bottom: 48px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.text-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
}


.sp-text-btn {
  background: none;
  border: none;
  color: #b3b3b3;
  font-weight: 700;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
}
.sp-text-btn:hover { color: #fff; text-decoration: underline; }

/* 深度选择器覆盖 n-spin */
:deep(.n-spin-container) {
  background: transparent !important;
}

/* 紧凑化分页由全局 style.css 处理 */
</style>
