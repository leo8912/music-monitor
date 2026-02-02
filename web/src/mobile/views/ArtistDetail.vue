<script setup lang="ts">
/**
 * 艺人详情页 - 移动端
 * 沉浸式设计，支持手势和快速播放
 */
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon, NAvatar, NTabs, NTabPane, NSpace, NSpin, NButton } from 'naive-ui'
import { PlayCircleOutline, HeartOutline, ChevronBackOutline, RefreshOutline } from '@vicons/ionicons5'
import { getArtistDetail } from '@/api/subscription'
import { refreshArtist } from '@/api/library'
import SongList from '@/components/SongList.vue'
import { usePlayerStore } from '@/stores/player'
import { useMessage } from 'naive-ui'

const DEFAULT_AVATAR = 'https://p1.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg'

const route = useRoute()
const router = useRouter()
const playerStore = usePlayerStore()
const message = useMessage()
const loading = ref(true)
const refreshing = ref(false)
const artist = ref<any>(null)
const activeTab = ref('songs')
const currentPage = ref(1)
const pageSize = ref(20)

const getHighResAvatar = (url: string) => {
    if (!url) return DEFAULT_AVATAR
    if (url.includes('y.gtimg.cn')) {
        return url.replace('300x300', '800x800')
    }
    return url
}

const fetchDetail = async () => {
  const id = route.params.id as string
  if (!id) return
  
  loading.value = true
  try {
    const res = await getArtistDetail(id)
    artist.value = res
  } catch (e) {
    console.error('获取艺人详情失败:', e)
  } finally {
    loading.value = false
  }
}

const playSong = (song: any) => {
    if (!artist.value?.songs) return
    // 设置播放列表为艺人的所有歌曲
    playerStore.setPlaylist(artist.value.songs)
    // 播放指定歌曲
    playerStore.playSong(song)
}

const handleRefresh = async () => {
  if (!artist.value || refreshing.value) return
  
  refreshing.value = true
  try {
    const res = await refreshArtist(artist.value.name)
    if (res.success) {
      message.success(`刷新成功，新增 ${res.new_songs_count} 首歌曲`)
      await fetchDetail()
    } else {
      message.error('刷新失败')
    }
  } catch (e) {
    console.error('刷新歌手失败:', e)
    message.error('刷新错误')
  } finally {
    refreshing.value = false
  }
}

const playAll = () => {
    if (!artist.value?.songs || artist.value.songs.length === 0) return
    // 设置播放列表
    playerStore.setPlaylist(artist.value.songs)
    // 播放第一首
    playerStore.playSong(artist.value.songs[0])
}

const goBack = () => {
    router.back()
}

onMounted(() => {
  fetchDetail()
})
</script>

<template>
  <div class="mobile-artist-detail">
    <div class="nav-header">
       <button class="back-btn" @click="goBack">
           <n-icon :component="ChevronBackOutline" />
       </button>
    </div>

    <n-spin :show="loading">
      <div v-if="artist" class="hero-section">
          <div class="hero-bg" :style="{ backgroundImage: `url(${artist.avatar || '/default-avatar.png'})` }"></div>
          <div class="hero-content">
              <img 
                :src="getHighResAvatar(artist.avatar)" 
                class="artist-avatar-m"
                @error="(e: any) => e.target.src = DEFAULT_AVATAR"
              />
              <h1 class="m-artist-name">{{ artist.name }}</h1>
              <p class="m-artist-stats">{{ artist.songs.length }} 歌曲 · {{ artist.albums.length }} 专辑</p>
              
              <div class="m-header-pagination" v-if="artist.songs.length > pageSize">
                <n-pagination
                   v-model:page="currentPage"
                   :page-count="Math.ceil(artist.songs.length / pageSize)"
                   simple
                />
              </div>
              
              <div class="m-action-btns">
                  <button 
                    class="m-refresh-secondary-btn" 
                    :class="{ 'active': refreshing }"
                    @click="handleRefresh" 
                    :disabled="refreshing"
                  >
                      <n-icon :size="24" :component="RefreshOutline" :class="{ 'spinning': refreshing }" />
                  </button>
                  <button class="m-play-btn" @click="playAll">
                      <n-icon :size="20" :component="PlayCircleOutline" /> 播放全部歌曲
                  </button>
              </div>
          </div>
      </div>

      <div v-if="artist" class="m-detail-body">
        <n-tabs type="line" justify-content="space-evenly" v-model:value="activeTab">
          <n-tab-pane name="songs" tab="热门歌曲">
             <div class="m-tab-pane-content">
                <SongList 
                    :history="artist.songs.slice((currentPage - 1) * pageSize, currentPage * pageSize)" 
                    :loading="false" 
                    mode="mobile"
                    @play="playSong"
                />
                
                <div class="footer-pagination" v-if="artist.songs.length > pageSize">
                   <n-pagination
                       v-model:page="currentPage"
                       :page-count="Math.ceil(artist.songs.length / pageSize)"
                       simple
                   />
                </div>
             </div>
          </n-tab-pane>
          <n-tab-pane name="albums" tab="专辑">
             <div class="m-tab-pane-content album-grid">
                 <div v-for="album in artist.albums" :key="album.name" class="m-album-card">
                    <img :src="album.cover || '/default-cover.png'" class="m-album-cover">
                    <div class="m-album-name truncate">{{ album.name }}</div>
                    <div class="m-album-year">{{ album.publishTime ? album.publishTime.substring(0, 4) : '-' }}</div>
                 </div>
             </div>
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.mobile-artist-detail {
    min-height: 100vh;
    background: #121212;
    padding-bottom: 100px;
}

.nav-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    padding: 12px;
}

.back-btn {
    background: rgba(0,0,0,0.5);
    border: none;
    color: #fff;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}

.hero-section {
    position: relative;
    height: 45vh;
    display: flex;
    align-items: flex-end;
    padding: 20px;
    overflow: hidden;
}

.hero-bg {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    filter: blur(20px) brightness(0.5);
    transform: scale(1.1);
}

.hero-content {
    position: relative;
    z-index: 10;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
}

.artist-avatar-m {
    border: 3px solid #fff;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.m-artist-name {
    font-size: 28px;
    font-weight: 800;
    color: #fff;
    margin: 16px 0 4px;
}

.m-artist-stats {
    color: rgba(255,255,255,0.7);
    font-size: 13px;
    margin-bottom: 20px;
}

.m-action-btns {
    display: flex;
    gap: 12px;
    width: 100%;
    max-width: 300px;
}

.m-play-btn {
    flex: 1;
    background: var(--sp-green);
    color: #000;
    border: none;
    height: 48px;
    border-radius: 24px;
    font-weight: 700;
    font-size: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    box-shadow: 0 4px 15px rgba(29, 185, 84, 0.4);
}

.m-refresh-secondary-btn {
    width: 48px;
    height: 48px;
    background: rgba(255, 255, 255, 0.08); /* 更精致的半透明 */
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: #ffffff;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.m-refresh-secondary-btn.active {
    color: var(--sp-green);
    border-color: var(--sp-green);
    background: rgba(29, 185, 84, 0.1);
}

.m-refresh-secondary-btn:active {
    transform: scale(0.9);
}

.spinning {
    animation: spin-refresh 1.2s linear infinite;
}

@keyframes spin-refresh {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.m-fav-btn {
    width: 44px;
    height: 44px;
    background: rgba(255,255,255,0.1);
    color: #fff;
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}

.m-header-pagination {
    margin-bottom: 16px;
}

.footer-pagination {
    display: flex;
    justify-content: center;
    margin-top: 24px;
}

.m-detail-body {
    background: #121212;
}

.m-tab-pane-content {
    padding: 10px;
}

.album-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
}

.m-album-card {
    min-width: 0;
}

.m-album-cover {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 8px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    margin-bottom: 8px;
}

.m-album-name {
    font-size: 14px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 2px;
}

.m-album-year {
    font-size: 12px;
    color: var(--text-secondary);
}

:deep(.song-item) {
    background: transparent !important;
    padding: 10px 0 !important;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}

:deep(.song-header) {
    display: none !important;
}

:deep(.song-album), :deep(.song-date) {
    display: none !important;
}

:deep(.song-item) {
    grid-template-columns: 30px 1fr 40px !important;
}
</style>
