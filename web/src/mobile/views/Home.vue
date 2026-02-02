<template>
  <div class="sp-mobile-home">
    <!-- Spotify 风格渐变背景 -->
    <div class="sp-gradient-bg"></div>

    <!-- 主内容 -->
    <main class="sp-main-content">
      <!-- 头部 -->
      <header class="sp-header">
        <h1 class="text-title">晚上好</h1>
        <div class="header-actions">
           <n-icon size="24" :component="NotificationsOutline" />
           <n-icon size="24" :component="TimeOutline" />
           <n-icon size="24" :component="SettingsOutline" @click="router.push({ name: 'MobileSettings' })" />
        </div>
      </header>

      <!-- 快捷歌手区 (Spotify Mix Style) -->
      <section class="sp-section">
        <div class="sp-artist-grid">
           <!-- Skeleton Loading -->
           <template v-if="libraryStore.isLoading">
             <div v-for="i in 6" :key="`skel-art-${i}`" class="sp-artist-pill surface-card">
                <Skeleton shape="circle" width="56px" height="56px" :style="{ marginRight: '8px' }" />
                <Skeleton width="60px" height="14px" />
             </div>
           </template>
           
           <!-- Real Data -->
           <template v-else-if="libraryStore.mergedArtists.length > 0">
             <div 
                v-for="artist in libraryStore.mergedArtists.slice(0, 6)" 
                :key="artist.name"
                class="sp-artist-pill surface-card clickable"
                @click="libraryStore.selectArtist(artist)"
             >
                <img :src="artist.avatar || '/default-avatar.png'" class="pill-img" loading="lazy" />
                <span class="pill-name truncate">{{ artist.name }}</span>
             </div>
           </template>
        </div>
      </section>

      <!-- 最近播放/推荐 -->
      <section class="sp-section">
        <h2 class="section-title">你的推荐列表</h2>
        
        <div class="sp-song-list">
          <!-- Skeleton Loading -->
          <template v-if="libraryStore.isLoading">
             <div v-for="i in 10" :key="`skel-song-${i}`" class="sp-song-item">
                <div class="song-cover skeleton-box">
                    <Skeleton width="100%" height="100%" />
                </div>
                <div class="song-info" style="display: flex; flex-direction: column; gap: 6px;">
                    <Skeleton width="70%" height="16px" />
                    <Skeleton width="40%" height="12px" />
                </div>
             </div>
          </template>

          <template v-else>
              <div 
                v-for="song in libraryStore.songs.slice(0, 20)" 
                :key="song.id"
                class="sp-song-item clickable"
                :class="{ 'is-active': playerStore.currentSong?.id === song.id }"
                @click="handlePlay(song)"
              >
                <img :src="song.cover || '/default-cover.png'" class="song-cover" loading="lazy" />
                
                <div class="song-info">
                  <div class="song-title" :class="{ 'text-green': playerStore.currentSong?.id === song.id }">
                    {{ song.title }}
                  </div>
                  <div class="song-meta">
                    <span class="song-tag" v-if="song.source === 'netease'">云音乐</span>
                    {{ formatArtist(song.artist) }}
                  </div>
                </div>
                
                <n-button quaternary circle size="small" @click.stop="">
                    <template #icon><n-icon :component="EllipsisVertical" /></template>
                </n-button>
              </div>
          </template>
        </div>
      </section>
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NButton } from 'naive-ui'
import Skeleton from '@/components/common/Skeleton.vue'
import { 
    Home, HomeOutline, 
    Search, SearchOutline, 
    Library, LibraryOutline,
    SettingsOutline, NotificationsOutline, TimeOutline,
    EllipsisVertical
} from '@vicons/ionicons5'
import { useLibraryStore, usePlayerStore, useSettingsStore } from '@/stores'

const router = useRouter()
const libraryStore = useLibraryStore()
const playerStore = usePlayerStore()
const settingsStore = useSettingsStore()

const handlePlay = (song: any) => {
  playerStore.setPlaylist(libraryStore.songs)
  playerStore.playSong(song)
}

const activeTab = ref('home')
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
  activeTab.value = name
  const routes: Record<string, string> = { home: 'MobileHome', library: 'MobileLibrary', search: 'MobileSearch' }
  router.push({ name: routes[name] })
}

const formatArtist = (artist: any) => Array.isArray(artist) ? artist.join(', ') : artist

onMounted(async () => {
  settingsStore.initTheme()
  await libraryStore.fetchArtists()
  await libraryStore.fetchSongs()
})
</script>

<style scoped>
.sp-mobile-home {
  min-height: 100vh;
  background: #121212;
  color: #fff;
  padding-bottom: 120px;
  position: relative;
}

.sp-gradient-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 300px;
  background: linear-gradient(to bottom, rgba(30,215,96, 0.15), transparent);
  pointer-events: none;
}

.sp-main-content {
  position: relative;
  z-index: 1;
  padding: 16px;
  padding-top: max(24px, env(safe-area-inset-top));
}

.sp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-actions {
  display: flex;
  gap: 20px;
  color: #fff;
}

.section-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 16px;
  letter-spacing: -0.5px;
}

/* 6格歌手布局 */
.sp-artist-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 32px;
}

.sp-artist-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 56px;
  border-radius: 4px;
  overflow: hidden;
  background-color: var(--sp-card);
  transition: background-color 0.2s;
}

.sp-artist-pill:active { background-color: var(--sp-card-hover); }

.pill-img {
  width: 56px;
  height: 56px;
  object-fit: cover;
}

.pill-name {
  font-size: 13px;
  font-weight: 700;
  padding-right: 8px;
}

/* 歌曲列表 */
.sp-song-list {
  display: flex;
  flex-direction: column;
}

.sp-song-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.song-cover {
  width: 48px;
  height: 48px;
  border-radius: 0; /* Square for Spotify vibe */
  object-fit: cover;
}

.song-info {
  flex: 1;
  min-width: 0;
}

.song-title {
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.text-green { color: var(--sp-green); }

.song-meta {
  font-size: 13px;
  color: #b3b3b3;
  display: flex;
  align-items: center;
  gap: 6px;
}

.song-tag {
  background: #c2c2c2;
  color: #000;
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 2px;
  font-weight: 700;
}

/* TabBar */
.sp-tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 80px; /* Taller to account for safe area */
  background: linear-gradient(to top, #000 0%, rgba(0,0,0,0.95) 100%);
  display: flex;
  justify-content: space-around;
  padding-top: 12px;
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 100;
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: #b3b3b3;
  width: 60px;
}

.tab-item.is-active {
  color: #fff;
}

.tab-label {
  font-size: 10px;
  font-weight: 500;
}
</style>
