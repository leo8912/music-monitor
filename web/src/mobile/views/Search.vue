<template>
  <div class="sp-search-page">
    <!-- Search Header -->
    <header class="sp-search-header">
      <h1 class="text-title">搜索</h1>
      
      <div class="sp-search-bar">
        <n-icon size="20" :component="SearchOutline" class="search-icon" />
        <input 
          v-model="keyword"
          type="text"
          class="search-input"
          placeholder="您想收听什么？"
          @keyup.enter="onSearch"
        />
        <button v-if="keyword" class="clear-btn" @click="clearSearch">
          <n-icon size="20" :component="CloseCircle" />
        </button>
      </div>

      <!-- Type Filter Tabs -->
      <div class="sp-filter-tabs">
        <button 
          v-for="tab in ['song', 'artist']" 
          :key="tab"
          class="filter-tab"
          :class="{ 'is-active': activeTab === tab }"
          @click="changeTab(tab as any)"
        >
          {{ tab === 'song' ? '单曲' : '艺人' }}
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="sp-search-content">
      <!-- Loading Skeletons -->
      <template v-if="isLoading">
          <div class="sp-results">
              <template v-if="activeTab === 'song'">
                  <div v-for="i in 8" :key="`skel-s-${i}`" class="sp-result-item">
                     <div class="result-img skeleton-box">
                         <Skeleton width="100%" height="100%" />
                     </div>
                     <div class="result-info" style="gap: 6px; display: flex; flex-direction: column;">
                         <Skeleton width="70%" height="16px" />
                         <Skeleton width="40%" height="12px" />
                     </div>
                  </div>
              </template>
              <template v-else>
                  <div v-for="i in 8" :key="`skel-a-${i}`" class="sp-result-item">
                     <div class="result-avatar skeleton-box">
                         <Skeleton shape="circle" width="100%" height="100%" />
                     </div>
                     <div class="result-info" style="gap: 6px; display: flex; flex-direction: column;">
                         <Skeleton width="50%" height="16px" />
                         <Skeleton width="30%" height="12px" />
                     </div>
                  </div>
              </template>
          </div>
      </template>

      <!-- History -->
      <div class="sp-history animate-fade-in" v-if="!keyword && !isLoading && searchHistory.length > 0">
        <div class="section-header">
          <h2 class="text-sub">最近搜索</h2>
          <button class="link-btn" @click="clearHistory">清除</button>
        </div>
        <div class="history-list">
          <div 
            v-for="item in searchHistory" 
            :key="item"
            class="history-item clickable"
            @click="searchFromHistory(item)"
          >
            <div class="history-icon">
                <n-icon size="16" :component="TimeOutline" />
            </div>
            <span class="history-text truncate">{{ item }}</span>
            <n-icon size="16" :component="CloseCircle" class="remove-icon" @click.stop="removeFromHistory(item)" />
          </div>
        </div>
      </div>

      <!-- Results -->
      <div class="sp-results" v-if="!isLoading && (songResults.length > 0 || artistResults.length > 0)">
          <!-- Song Results -->
          <template v-if="activeTab === 'song'">
              <div 
                v-for="song in songResults" 
                :key="song.id"
                class="sp-result-item clickable"
                @click="handlePlaySong(song)"
              >
                  <img :src="song.cover || '/default-cover.png'" class="result-img" loading="lazy" />
                  <div class="result-info">
                      <h3 class="result-title truncate" :class="{ 'text-green': String(playerStore.currentSong?.id) === String(song.id) }">
                          {{ song.title }}
                      </h3>
                      <p class="result-sub truncate">{{ formatArtist(song.artist) }}</p>
                  </div>
                  <button class="more-btn">
                      <n-icon size="20" :component="EllipsisVertical" />
                  </button>
              </div>
          </template>

          <!-- Artist Results -->
          <template v-else>
              <div 
                v-for="artist in artistResults" 
                :key="artist.id"
                class="sp-result-item clickable"
                @click="handleAddArtist(artist)"
              >
                  <img :src="artist.avatar || '/default-avatar.png'" class="result-avatar" loading="lazy" />
                  <div class="result-info">
                      <h3 class="result-title truncate">{{ artist.name }}</h3>
                      <p class="result-sub">艺人</p>
                  </div>
                  <button class="add-btn">
                      <n-icon size="20" :component="AddOutline" />
                  </button>
              </div>
          </template>
      </div>

      <!-- Empty State -->
      <div class="sp-empty" v-if="keyword && !isLoading && songResults.length === 0 && artistResults.length === 0">
        <div class="empty-content">
            <h3 class="empty-title">找不到结果</h3>
            <p class="empty-desc">请尝试搜索其他关键词。</p>
        </div>
      </div>
    </main>

    <!-- Spotify Mobile TabBar -->
    <nav class="sp-tabbar">
      <div 
        v-for="tab in tabs" 
        :key="tab.name"
        class="tab-item clickable"
        :class="{ 'is-active': activeTab === tab.name }"
        @click="onTabChange(tab.name)"
      >
        <n-icon size="26" :component="getTabIcon(tab.icon, activeTab === tab.name)" />
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import Skeleton from '@/components/common/Skeleton.vue'
import { 
    Search, SearchOutline, 
    CloseCircle, TimeOutline, 
    AddOutline, EllipsisVertical,
    Home, HomeOutline, Library, LibraryOutline
} from '@vicons/ionicons5'
import { searchSongs, searchArtists } from '@/api/discovery'
import { usePlayerStore, useLibraryStore } from '@/stores'
import type { SearchSong, SearchArtist } from '@/types'

const router = useRouter()
const playerStore = usePlayerStore()
const libraryStore = useLibraryStore()

const keyword = ref('')
const activeTab = ref<'song' | 'artist'>('song')
const isLoading = ref(false)
const songResults = ref<SearchSong[]>([])
const artistResults = ref<SearchArtist[]>([])
const searchHistory = ref<string[]>(JSON.parse(localStorage.getItem('search_history') || '[]'))

const onSearch = async () => {
    const query = keyword.value.trim()
    if (!query) return
    
    if (!searchHistory.value.includes(query)) {
        searchHistory.value = [query, ...searchHistory.value.slice(0, 9)]
        localStorage.setItem('search_history', JSON.stringify(searchHistory.value))
    }
    
    isLoading.value = true
    try {
        if (activeTab.value === 'song') songResults.value = await searchSongs({ keyword: query })
        else artistResults.value = await searchArtists({ keyword: query })
    } catch (e) {
        console.error(e)
    } finally {
        isLoading.value = false
    }
}

const changeTab = (tab: 'song' | 'artist') => {
    activeTab.value = tab
    if (keyword.value) onSearch()
}

const clearSearch = () => {
    keyword.value = ''
    songResults.value = []
    artistResults.value = []
}

const searchFromHistory = (query: string) => {
    keyword.value = query
    onSearch()
}

const removeFromHistory = (item: string) => {
    searchHistory.value = searchHistory.value.filter(h => h !== item)
    localStorage.setItem('search_history', JSON.stringify(searchHistory.value))
}

const clearHistory = () => {
    searchHistory.value = []
    localStorage.removeItem('search_history')
}

const handlePlaySong = (song: SearchSong) => {
    playerStore.playSong({
        id: 0, title: song.title, artist: Array.isArray(song.artist) ? song.artist.join('/') : song.artist,
        album: song.album, source: song.source, sourceId: song.id, cover: song.cover,
        isFavorite: false, status: 'PENDING'
    })
}

const handleAddArtist = async (artist: SearchArtist) => {
    await libraryStore.addArtist(artist.name, artist.source, artist.id, artist.avatar)
}

const formatArtist = (artist: any) => Array.isArray(artist) ? artist.join(', ') : artist

const tabs = [
  { name: 'home', icon: 'home', label: '首页' },
  { name: 'search', icon: 'search', label: '搜索' },
  { name: 'library', icon: 'library', label: '资料库' }
]

const getTabIcon = (type: string, active: boolean) => {
    if (type === 'home') return active ? Home : HomeOutline
    if (type === 'search') return active ? Search : SearchOutline
    return active ? Library : LibraryOutline
}

const onTabChange = (name: string) => {
    const routes: Record<string, string> = { home: 'MobileHome', library: 'MobileLibrary', search: 'MobileSearch' }
    router.push({ name: routes[name] })
}
</script>

<style scoped>
.sp-search-page {
  min-height: 100vh;
  background: #121212;
  color: #fff;
  padding-bottom: 120px;
}

.sp-search-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #121212;
  padding: 16px;
  padding-top: max(24px, env(safe-area-inset-top));
  padding-bottom: 12px;
}

.text-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 16px;
}

.sp-search-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #fff;
  border-radius: 4px;
}

.search-icon { color: #121212; }
.search-input { 
  flex: 1; 
  background: none; border: none; outline: none; 
  font-size: 16px; color: #121212; font-weight: 500;
}
.search-input::placeholder { color: #555; }
.clear-btn { background: none; border: none; color: #121212; display: flex; }

.sp-filter-tabs {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
.filter-tab {
  padding: 6px 16px;
  border-radius: 16px;
  border: 1px solid #777;
  background: transparent;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}
.filter-tab.is-active {
  background: var(--sp-green);
  border-color: var(--sp-green);
  color: #000;
}

.sp-search-content {
  padding: 0 16px;
}

.sp-loading { padding: 40px; display: flex; justify-content: center; }

.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; margin-top: 8px; }
.text-sub { font-size: 16px; font-weight: 700; }
.link-btn { background: none; border: none; color: #b3b3b3; font-size: 12px; font-weight: 600; }

.history-list { display: flex; flex-direction: column; }
.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  color: #b3b3b3;
}
.history-icon { color: #b3b3b3; display: flex; }
.history-text { flex: 1; font-size: 14px; color: #fff; }
.remove-icon { color: #777; }

.sp-results { display: flex; flex-direction: column; }

.sp-result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.result-img { width: 48px; height: 48px; object-fit: cover; }
.result-avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; }

.result-info { flex: 1; min-width: 0; }
.result-title { font-size: 15px; font-weight: 500; margin-bottom: 4px; color: #fff; }
.result-sub { font-size: 13px; color: #b3b3b3; }
.text-green { color: var(--sp-green); }

.more-btn, .add-btn { background: none; border: none; color: #b3b3b3; padding: 8px; }

.sp-empty { padding: 60px 0; text-align: center; }
.empty-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.empty-desc { font-size: 14px; color: #b3b3b3; }

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
