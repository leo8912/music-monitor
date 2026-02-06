<script setup lang="ts">
/**
 * 艺人详情页 - 桌面端
 * 展示艺人热门歌曲及专辑
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { NIcon, NAvatar, NTabs, NTabPane, NGrid, NGridItem, NCard, NSpace, NSpin } from 'naive-ui'
import { PlayCircleOutline, HeartOutline, ShareSocialOutline, RefreshOutline } from '@vicons/ionicons5'
import { getArtistDetail } from '@/api/subscription'
import { refreshArtist } from '@/api/library'
import SongList from '@/components/SongList.vue'
import { usePlayerStore } from '@/stores/player'
import { useProgressStore } from '@/stores/progress'
import { useMessage } from 'naive-ui'

const DEFAULT_AVATAR = 'https://p1.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg'

const route = useRoute()
const playerStore = usePlayerStore()
const progressStore = useProgressStore()

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
  
  try {
    // Note: detail API might need to be updated or we paginate the array locally if small,
    // but typically we should use the same library API style for consistency.
    // For now, let's keep the detail fetch as is but prepare for large lists.
    const res = await getArtistDetail(id)
    artist.value = res
  } catch (e) {
    console.error('获取艺人详情失败:', e)
  } finally {
    loading.value = false
  }
}

const getProgress = () => {
   if (!artist.value) return null
   // Store logic uses number ID, API returns number or string?
   // Usually number.
   return progressStore.getProgress(Number(artist.value.id))
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
      // 重新加载详情以获取新歌曲
      await fetchDetail()
    } else {
      message.error('刷新失败')
    }
  } catch (e) {
    console.error('刷新歌手失败:', e)
    message.error('刷新过程中发生错误')
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

onMounted(() => {
  fetchDetail()
})
</script>

<template>
  <div class="artist-detail-view scrollbar-hide">
    <n-spin :show="loading">
      <div v-if="artist" class="artist-header">
        <div class="header-content">
          
          <!-- Avatar with Ring -->
          <div class="avatar-wrapper">
             <svg v-if="getProgress()" class="progress-ring" viewBox="0 0 170 170">
                <circle cx="85" cy="85" r="82" class="ring-bg" />
                <circle cx="85" cy="85" r="82" class="ring-progress" />
             </svg>
             
             <img 
                :src="getHighResAvatar(artist.avatar)" 
                class="artist-avatar-large"
                :class="{ 'dimmed': getProgress() }"
                @error="(e: any) => e.target.src = DEFAULT_AVATAR"
             />
          </div>

          <div class="artist-info">
            <span class="type-label">艺人</span>
            <h1 class="artist-name">{{ artist.name }}</h1>
            
            <!-- Status Capsule -->
            <div v-if="getProgress()" class="status-capsule">
                <n-spin size="small" stroke="#1DB954" />
                <span>{{ getProgress()?.message || '处理中...' }}</span>
            </div>

            <div class="artist-stats">
              <span>{{ artist.songs.length }} 首歌曲</span>
              <span class="dot">•</span>
              <span>{{ artist.albums.length }} 张专辑</span>
            </div>
            <div class="action-bar">
              <button 
                class="refresh-btn-secondary" 
                :class="{ 'active': refreshing }"
                @click="handleRefresh" 
                :disabled="refreshing"
                :title="refreshing ? '正在刷新...' : '同步及修复元数据'"
              >
                 <n-icon :size="24" :component="RefreshOutline" :class="{ 'spinning': refreshing }" />
              </button>

              <button class="play-btn-main" @click="playAll" title="播放全部">
                 <n-icon :size="28" :component="PlayCircleOutline" />
                 <span>播放</span>
              </button>

              <div class="header-pagination-container" v-if="artist.songs.length > pageSize">
                <n-pagination
                   v-model:page="currentPage"
                   :page-count="Math.ceil(artist.songs.length / pageSize)"
                   simple
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="artist" class="detail-body">
        <n-tabs type="line" v-model:value="activeTab">
          <n-tab-pane name="songs" tab="热门歌曲">
            <div class="tab-content">
              <SongList 
                :history="artist.songs.slice((currentPage - 1) * pageSize, currentPage * pageSize)" 
                :loading="false" 
                mode="artist"
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
          <n-tab-pane name="albums" tab="所有专辑">
            <div class="tab-content">
              <n-grid :x-gap="20" :y-gap="24" :cols="5">
                <n-grid-item v-for="album in artist.albums" :key="album.name">
                  <div class="album-card surface-card">
                    <div class="album-cover-wrapper">
                      <img :src="album.cover || '/default-cover.png'" class="album-cover">
                      <div class="play-overlay">
                        <n-icon :component="PlayCircleOutline" />
                      </div>
                    </div>
                    <div class="album-meta">
                      <div class="album-name truncate">{{ album.name }}</div>
                      <div class="album-year">{{ album.publish_time ? album.publish_time.substring(0, 4) : '-' }}</div>
                    </div>
                  </div>
                </n-grid-item>
              </n-grid>
            </div>
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.artist-detail-view {
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.artist-header {
  margin-bottom: 40px;
  padding: 20px 0;
}

.header-content {
  display: flex;
  align-items: flex-end;
  gap: 32px;
  flex-wrap: nowrap; /* 强制不换行 */
}

/* New Avatar Wrapper */
.avatar-wrapper {
   position: relative;
   width: 170px; 
   height: 170px;
   display: flex;
   align-items: center;
   justify-content: center;
}

.progress-ring {
    position: absolute;
    width: 170px;
    height: 170px;
    animation: spin 3s linear infinite;
    z-index: 5; /* 确保环在图片之上 */
    pointer-events: none;
}
.ring-bg {
    fill: none;
    stroke: rgba(255,255,255,0.1);
    stroke-width: 3;
}
.ring-progress {
    fill: none;
    stroke: #1DB954;
    stroke-width: 4;
    stroke-dasharray: 140 400; /* ~25% of circumference (515) */
    stroke-linecap: round;
}
@keyframes spin { 100% { transform: rotate(360deg); } }

.artist-avatar-large {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  transition: all 0.3s ease;
  z-index: 2;
  background-color: #282828; /* Placeholder color while loading */
}

.artist-avatar-large.dimmed {
    opacity: 0.7;
    transform: scale(0.96);
    box-shadow: none; /* remove shadow if dimmed to emphasize ring? or keep */
}

/* Status Capsule */
.status-capsule {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 6px 16px;
    border-radius: 20px;
    margin-bottom: 16px;
    color: var(--sp-green);
    font-size: 13px;
    font-weight: 500;
    animation: slide-up 0.5s ease;
}
@keyframes slide-up {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.artist-info {
  flex: 1;
}

.type-label {
  text-transform: uppercase;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--text-secondary);
}

.artist-name {
  font-size: clamp(32px, 5vw, 64px);
  margin: 4px 0 12px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1;
}

.artist-stats {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 30px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot { font-size: 20px; line-height: 0; }

.action-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-top: 16px;
}

.play-btn-main {
  background: var(--sp-green);
  color: #000;
  border: none;
  padding: 12px 32px;
  border-radius: 500px;
  font-weight: 700;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.3, 0, 0, 1);
  box-shadow: 0 4px 12px rgba(29, 185, 84, 0.3);
}

.play-btn-main:hover {
  transform: scale(1.05);
  background: #1ed760;
}

/* Secondary Refresh Button */
.refresh-btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  color: #b3b3b3;
  border: 1px solid rgba(255, 255, 255, 0.2);
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.refresh-btn-secondary:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.4);
  transform: scale(1.05);
}

.refresh-btn-secondary.active {
    color: var(--sp-green);
    border-color: var(--sp-green);
    background: rgba(29, 185, 84, 0.1);
}

.refresh-btn-secondary :deep(.n-icon) {
    display: flex;
}

.spinning {
    animation: spin-refresh 1.2s linear infinite;
}

@keyframes spin-refresh {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.detail-body {
  margin-top: 20px;
}

.tab-content {
  padding-top: 20px;
}

.footer-pagination {
    display: flex;
    justify-content: center;
    margin-top: 32px;
}

/* 专辑卡片样式 */
.album-card {
  border-radius: 12px;
  overflow: hidden;
  padding: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.album-card:hover { background: rgba(255,255,255,0.05); }

.album-cover-wrapper {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.album-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s;
}

.album-card:hover .album-cover { transform: scale(1.1); }

.play-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
  font-size: 40px;
  color: #fff;
}

.album-card:hover .play-overlay { opacity: 1; }

.album-meta { min-width: 0; }
.album-name { font-weight: 600; color: #fff; margin-bottom: 2px; }
.album-year { font-size: 12px; color: var(--text-secondary); }

</style>
