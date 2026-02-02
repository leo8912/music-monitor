<template>
  <div class="sp-player">
    <!-- Spotify 风格渐变背景 -->
    <div 
      class="sp-player-bg" 
      :style="{ '--bg-color': dominantColor }"
    ></div>
    
    <!-- 内容容器 -->
    <div class="sp-player-content">
        <!-- 顶部控制 -->
        <header class="sp-player-header">
            <button class="nav-btn" @click="router.back()">
                <n-icon size="24" :component="ChevronDownOutline" />
            </button>
            <div class="header-info">
                <span class="playing-from">正在播放</span>
                <span class="playing-source">{{ playerStore.currentSong?.source ? (playerStore.currentSong.source === 'netease' ? '网易云音乐' : 'QQ音乐') : '本地音乐' }}</span>
            </div>
            <button class="nav-btn">
                <n-icon size="24" :component="EllipsisHorizontalOutline" />
            </button>
        </header>

        <!-- 主播放区域 -->
        <main class="sp-player-main">
            <!-- 封面容器 -->
             <div class="sp-cover-container" v-show="!showLyrics" @click="toggleLyrics">
                <img 
                    :src="playerStore.currentSong?.cover || '/default-cover.png'" 
                    class="sp-cover-image"
                />
            </div>
            
            <!-- 歌词容器 -->
            <div v-show="showLyrics" class="sp-lyrics-container" @click="toggleLyrics">
                 <div class="lyrics-scroll" ref="lyricsArea">
                    <div 
                        v-for="(line, idx) in playerStore.lyrics" 
                        :key="idx"
                        class="lyric-line"
                        :class="{ 'is-active': idx === playerStore.currentLyricIndex }"
                    >
                        {{ line.text }}
                    </div>
                 </div>
            </div>
        </main>

        <!-- 底部区域 -->
        <footer class="sp-player-footer">
            <!-- 歌曲信息行 -->
            <div class="sp-meta-row">
                <div class="text-info">
                    <h1 class="song-title truncate">{{ playerStore.currentSong?.title || '未知歌曲' }}</h1>
                    <p class="song-artist truncate">{{ playerStore.currentSong?.artist || '未知歌手' }}</p>
                </div>
                <button class="fav-btn" :class="{ 'is-active': playerStore.currentSong?.isFavorite }">
                    <n-icon size="24" :component="playerStore.currentSong?.isFavorite ? Heart : HeartOutline" />
                </button>
            </div>

            <!-- 进度条 -->
            <div class="sp-progress-bar">
                <n-slider 
                    v-model:value="seekProgress" 
                    :max="100" 
                    :step="0.1" 
                    :tooltip-visible="false"
                    @update:value="handleSeek"
                />
                <div class="time-labels">
                    <span>{{ formatTime(playerStore.currentTime) }}</span>
                    <span>{{ formatTime(playerStore.duration) }}</span>
                </div>
            </div>

            <!-- 控制面板 -->
            <div class="sp-controls">
                <button class="control-btn" @click="toggleShuffle">
                     <n-icon size="24" :component="ShuffleOutline" :color="isShuffle ? '#1DB954' : '#fff'" />
                </button>
                <button class="control-btn" @click="playerStore.playPrev">
                     <n-icon size="36" :component="PlaySkipBack" />
                </button>
                <button class="play-btn-circle" @click="playerStore.togglePlay">
                     <n-icon size="32" :component="playerStore.isPlaying ? Pause : Play" color="#000" />
                </button>
                <button class="control-btn" @click="playerStore.playNext">
                     <n-icon size="36" :component="PlaySkipForward" />
                </button>
                <button class="control-btn" @click="toggleLoop">
                     <n-icon size="24" :component="RepeatOutline" :color="isLoop ? '#1DB954' : '#fff'" />
                </button>
            </div>

            <!-- 底部工具栏 -->
            <div class="sp-tools">
                <button class="tool-btn">
                    <n-icon size="20" :component="DesktopOutline" />
                </button>
                
                <button class="tool-btn" @click="toggleLyrics">
                     <n-icon size="20" :component="ListOutline" />
                </button>
            </div>
        </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NSlider } from 'naive-ui'
import { 
    ChevronDownOutline, EllipsisHorizontalOutline, HeartOutline, Heart,
    PlaySkipBack, PlaySkipForward, Play, Pause,
    ShuffleOutline, RepeatOutline, DesktopOutline, ListOutline
} from '@vicons/ionicons5'
import { usePlayerStore } from '@/stores'
// import ColorThief from 'colorthief' // Assuming simple color extraction or mock for now

const router = useRouter()
const playerStore = usePlayerStore()
const showLyrics = ref(false)
const lyricsArea = ref<HTMLElement | null>(null)
const dominantColor = ref('#535353') // Default dark grey
const isShuffle = ref(false)
const isLoop = ref(false)

const toggleLyrics = () => { showLyrics.value = !showLyrics.value }
const toggleShuffle = () => { isShuffle.value = !isShuffle.value }
const toggleLoop = () => { isLoop.value = !isLoop.value }

const seekProgress = computed({
    get: () => playerStore.progress,
    set: (val) => { /* handled by update:value */ }
})

const handleSeek = (val: number) => {
    playerStore.seekTo(val)
}

const formatTime = (seconds: number) => {
    if (!seconds) return '0:00'
    const min = Math.floor(seconds / 60)
    const sec = Math.floor(seconds % 60)
    return `${min}:${sec.toString().padStart(2, '0')}`
}

// 简单的颜色提取模拟，实际项目可替换为 ColorThief
watch(() => playerStore.currentSong, () => {
   // Randomish dark color based on ID to simulate extraction
   const colors = ['#535353', '#7b2cbf', '#2a9d8f', '#e76f51', '#264653']
   dominantColor.value = colors[(playerStore.currentSong?.id || 0) % colors.length]
}, { immediate: true })

watch(() => playerStore.currentLyricIndex, (idx) => {
    if (showLyrics.value && lyricsArea.value) {
        const activeLine = lyricsArea.value.querySelector('.lyric-line.is-active') as HTMLElement
        if (activeLine) {
            activeLine.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
    }
})
</script>

<style scoped>
.sp-player {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: #121212;
  color: #fff;
}

.sp-player-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, var(--bg-color), #121212 85%);
  opacity: 0.6;
  z-index: 1;
  transition: background-color 0.8s ease;
}

.sp-player-content {
  position: relative;
  z-index: 2;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: env(safe-area-inset-top) 0 env(safe-area-inset-bottom);
}

.sp-player-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
}

.nav-btn {
  background: none;
  border: none;
  color: #fff;
  padding: 0;
}

.header-info { text-align: center; display: flex; flex-direction: column; align-items: center; }
.playing-from { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; margin-bottom: 2px; }
.playing-source { font-size: 12px; font-weight: 700; }

.sp-player-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
}

.sp-cover-container {
  width: 100%;
  aspect-ratio: 1;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
}
.sp-cover-image { width: 100%; height: 100%; object-fit: cover; }

.sp-lyrics-container {
    width: 100%;
    height: 60vh;
    background: rgba(0,0,0,0.3);
    border-radius: 8px;
    padding: 20px;
    overflow: hidden;
}
.lyrics-scroll { height: 100%; overflow-y: auto; scrollbar-width: none; }
.lyric-line { 
    font-size: 20px; font-weight: 700; margin-bottom: 24px; color: rgba(255,255,255,0.6); 
    transition: all 0.2s;
}
.lyric-line.is-active { color: #fff; transform: scale(1.02); }

.sp-player-footer {
  padding: 0 24px 40px;
}

.sp-meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.text-info { flex: 1; padding-right: 16px; min-width: 0; }
.song-title { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.song-artist { font-size: 16px; color: #b3b3b3; }
.fav-btn { background: none; border: none; color: #b3b3b3; }
.fav-btn.is-active { color: #1DB954; }

.sp-progress-bar { margin-bottom: 16px; }
.time-labels { display: flex; justify-content: space-between; font-size: 11px; color: #b3b3b3; margin-top: 6px; }

.sp-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.control-btn { background: none; border: none; color: #fff; padding: 8px; }
.play-btn-circle {
    width: 64px; height: 64px; border-radius: 50%; background: #fff;
    display: flex; align-items: center; justify-content: center; border: none;
}

.sp-tools { display: flex; justify-content: space-between; padding: 0 16px; }
.tool-btn { background: none; border: none; color: #b3b3b3; }
</style>
