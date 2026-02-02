<template>
  <div class="sp-library">
    <!-- Spotify 风格渐变背景 -->
    <div class="sp-gradient-bg"></div>

    <header class="sp-library-header">
      <div class="header-top">
        <div class="user-profile">
            <img src="/default-avatar.png" class="user-avatar" />
            <span class="page-title">资料库</span>
        </div>
        <div class="header-actions">
           <n-icon size="24" :component="SearchOutline" @click="router.push({ name: 'MobileSearch' })" />
           <n-icon size="24" :component="AddOutline" />
        </div>
      </div>

      <!-- Pill Filters -->
      <div class="sp-pill-filters">
        <button 
          class="filter-pill" 
          :class="{ 'is-active': activeTab === 'all' }"
          @click="switchTab('all')"
        >
          全部
        </button>
        <button 
          class="filter-pill" 
          :class="{ 'is-active': activeTab === 'favorite' }"
          @click="switchTab('favorite')"
        >
          已收藏
        </button>
        <button class="filter-pill" @click="onRefresh">
             <n-icon :component="RefreshOutline" />
        </button>

        <div class="header-pagination-mobile" v-if="libraryStore.totalSongs > libraryStore.pageSize">
          <n-pagination
            v-model:page="libraryStore.currentPage"
            :page-count="Math.ceil(libraryStore.totalSongs / libraryStore.pageSize)"
            @update:page="(page: number) => libraryStore.fetchSongs(page)"
            simple
          />
        </div>
      </div>
    </header>

    <main class="sp-library-content">
      <!-- Sort Row -->
      <div class="sort-row" v-if="filteredSongs.length > 0">
          <div class="sort-btn">
              <n-icon :component="SwapVerticalOutline" />
              <span>最近添加</span>
          </div>
          <div class="view-btn">
              <n-icon :component="GridOutline" />
          </div>
      </div>

      <div class="sp-song-list">
        <!-- Skeleton Loading -->
        <template v-if="isRefreshing || libraryStore.isLoading">
            <div v-for="i in 12" :key="`lib-skel-${i}`" class="sp-song-item">
                <div class="song-cover skeleton-box">
                    <Skeleton width="100%" height="100%" />
                </div>
                <div class="song-info" style="display: flex; flex-direction: column; gap: 6px;">
                    <Skeleton width="75%" height="16px" />
                    <Skeleton width="45%" height="12px" />
                </div>
            </div>
        </template>

        <template v-else>
            <div 
            v-for="song in filteredSongs" 
            :key="song.id"
            class="sp-song-item clickable"
            :class="{ 'is-active': playerStore.currentSong?.id === song.id }"
            @click="handlePlay(song)"
            >
            <img :src="song.cover || '/default-cover.png'" class="song-cover" loading="lazy" />
            
            <div class="song-info">
                <h3 class="song-title truncate" :class="{ 'text-green': playerStore.currentSong?.id === song.id }">
                    {{ song.title }}
                </h3>
                <div class="song-meta truncate">
                    <span class="pin-icon" v-if="song.isFavorite">
                        <n-icon :component="Pin" size="12" color="#1DB954" />
                    </span>
                    {{ formatArtist(song.artist) }}
                </div>
            </div>
            
            <div class="song-actions">
                <!-- Downloaded Indicator -->
                <n-icon v-if="song.status === 'DOWNLOADED'" :component="ArrowDownCircle" size="16" color="#1DB954" />
                <n-button quaternary circle class="more-btn" @click.stop="">
                    <template #icon><n-icon size="20" :component="EllipsisVertical" /></template>
                </n-button>
            </div>
            </div>
        </template>
      </div>

      <!-- Pagination Footer -->
      <div class="footer-pagination" v-if="libraryStore.totalSongs > libraryStore.pageSize">
          <n-pagination
            v-model:page="libraryStore.currentPage"
            :page-count="Math.ceil(libraryStore.totalSongs / libraryStore.pageSize)"
            @update:page="(page: number) => libraryStore.fetchSongs(page)"
            simple
          />
      </div>

      <!-- Empty State -->
      <div class="sp-empty" v-if="filteredSongs.length === 0">
        <div class="empty-content">
            <h3 class="empty-title">创建你的首个收藏</h3>
            <p class="empty-desc">收藏歌曲从未如此简单。</p>
            <button class="sp-btn-primary" @click="router.push({ name: 'MobileSearch' })">
                去寻找歌曲
            </button>
        </div>
      </div>
    </main>
    
    <!-- TabBar -->
    <nav class="sp-tabbar">
      <div 
        v-for="tab in tabs" 
        :key="tab.name"
        class="tab-item clickable"
        :class="{ 'is-active': tab.name === 'library' }"
        @click="onTabChange(tab.name)"
      >
        <n-icon size="26" :component="getTabIcon(tab.icon, tab.name === 'library')" />
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NButton, NPagination } from 'naive-ui'
import Skeleton from '@/components/common/Skeleton.vue'
import { 
    SearchOutline, AddOutline, RefreshOutline, 
    SwapVerticalOutline, GridOutline, Pin, ArrowDownCircle, EllipsisVertical,
    Home, HomeOutline, Search, SearchOutline as SearchIconOutline, Library, LibraryOutline 
} from '@vicons/ionicons5'
import { useLibraryStore, usePlayerStore } from '@/stores'

const router = useRouter()
const libraryStore = useLibraryStore()
const playerStore = usePlayerStore()

const activeTab = ref('all')
const isRefreshing = ref(false)

const onRefresh = async () => {
  isRefreshing.value = true
  await libraryStore.fetchSongs(1)
  isRefreshing.value = false
}

const handlePlay = (song: any) => {
  playerStore.setPlaylist(libraryStore.songs)
  playerStore.playSong(song)
}

const filteredSongs = computed(() => {
  if (activeTab.value === 'favorite') {
    return libraryStore.songs.filter(s => s.isFavorite)
  }
  return libraryStore.songs
})

const switchTab = (tab: string) => {
  activeTab.value = tab
}

const formatArtist = (artist: any) => Array.isArray(artist) ? artist.join(', ') : artist

const tabs = [
  { name: 'home', icon: 'home', label: '首页' },
  { name: 'search', icon: 'search', label: '搜索' },
  { name: 'library', icon: 'library', label: '资料库' }
]

const getTabIcon = (type: string, active: boolean) => {
    if (type === 'home') return active ? Home : HomeOutline
    if (type === 'search') return active ? Search : SearchIconOutline
    return active ? Library : LibraryOutline
}

const onTabChange = (name: string) => {
    const routes: Record<string, string> = { home: 'MobileHome', library: 'MobileLibrary', search: 'MobileSearch' }
    router.push({ name: routes[name] })
}

onMounted(() => {
  libraryStore.fetchSongs(1)
})
</script>

<style scoped>
.sp-library {
  min-height: 100vh;
  background: #121212;
  color: #fff;
  padding-bottom: 120px;
}

.sp-gradient-bg {
  position: sticky;
  top: 0;
  height: 100px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.8), #121212);
  margin-bottom: -100px;
  z-index: 1;
  pointer-events: none;
}

.sp-library-header {
  padding: 16px;
  padding-top: max(24px, env(safe-area-inset-top));
  background: #121212;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.user-profile { display: flex; align-items: center; gap: 12px; }
.user-avatar { width: 32px; height: 32px; border-radius: 50%; background: #333; }
.page-title { font-size: 22px; font-weight: 700; }

.header-actions { display: flex; gap: 20px; }

.sp-pill-filters {
  display: flex;
  gap: 8px;
}
.filter-pill {
  padding: 6px 16px;
  border-radius: 16px;
  border: 1px solid #777;
  background: transparent;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
}
.filter-pill.is-active {
  background: var(--sp-green);
  border-color: var(--sp-green);
  color: #000;
}

.header-pagination-mobile {
    margin-left: auto;
}

.footer-pagination {
    display: flex;
    justify-content: center;
    margin: 24px 0;
}

.sp-library-content {
  padding: 0 16px;
  min-height: 60vh;
}

.sort-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0;
  color: #b3b3b3;
}
.sort-btn { display: flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 600; }

.sp-song-list { display: flex; flex-direction: column; }
.sp-song-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.song-cover {
  width: 52px;
  height: 52px;
  border-radius: 0;
  background: #282828;
}

.song-info { flex: 1; min-width: 0; }
.song-title { font-size: 15px; font-weight: 500; margin-bottom: 2px; color: #fff; }
.song-meta { font-size: 13px; color: #b3b3b3; display: flex; align-items: center; gap: 4px; }
.text-green { color: var(--sp-green); }

.song-actions { display: flex; align-items: center; gap: 12px; }
.more-btn { color: #b3b3b3; }

.sp-empty { padding: 60px 0; display: flex; justify-content: center; text-align: center; }
.empty-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.empty-desc { font-size: 14px; color: #b3b3b3; margin-bottom: 24px; }
.sp-btn-primary {
  padding: 12px 32px;
  border-radius: 32px;
  background: #fff;
  color: #000;
  font-weight: 700;
  border: none;
  font-size: 14px;
}

/* TabBar */
.sp-tabbar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 80px; 
  background: linear-gradient(to top, #000 0%, rgba(0,0,0,0.95) 100%);
  display: flex;
  justify-content: space-around;
  padding-top: 12px;
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 100;
}
.tab-item { display: flex; flex-direction: column; align-items: center; gap: 4px; color: #b3b3b3; width: 60px; }
.tab-item.is-active { color: #fff; }
.tab-label { font-size: 10px; font-weight: 500; }
</style>
