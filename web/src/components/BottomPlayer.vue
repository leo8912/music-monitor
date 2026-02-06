<script setup lang="ts">
/**
 * 底部播放器组件 - Spotify 风格重构版
 * 集成了玻璃拟态、音轨可视化和 Store 联通
 */

import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { 
  PlaySharp, 
  PauseSharp, 
  PlaySkipBackSharp, 
  PlaySkipForwardSharp,
  VolumeMediumOutline,
  VolumeMuteOutline,
  HeartOutline,
  Heart,
  MusicalNotesOutline,
  ListOutline
} from '@vicons/ionicons5'
import { NIcon, NSlider, NTooltip, NTag } from 'naive-ui'
import { usePlayerStore } from '@/stores'
import { useRouter, useRoute } from 'vue-router'


const router = useRouter()
const route = useRoute()
const playerStore = usePlayerStore()
const currentLyricText = computed(() => {
  const idx = playerStore.currentLyricIndex
  if (idx >= 0 && playerStore.lyrics[idx]) {
    return playerStore.lyrics[idx].text
  }
  return ''
})


const audioRef = ref<HTMLAudioElement | null>(null)

const formatTime = (s: number) => {
  if (!s) return '0:00'
  const min = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${min}:${sec.toString().padStart(2, '0')}`
}

// 事件处理
const onTimeUpdate = () => {
  if (audioRef.value) playerStore.updateTime(audioRef.value.currentTime)
}
const onLoadedMetadata = () => {
  if (audioRef.value) playerStore.setDuration(audioRef.value.duration)
}
const onEnded = () => playerStore.playNext()

const togglePlay = () => {
  playerStore.togglePlay()
}

// 监听指令
watch(() => playerStore.isPlaying, async (playing) => {
  if (playing) {
    await nextTick()
    audioRef.value?.play().catch(e => {
        console.warn("Playback failed safely:", e)
        // If it failed because of bad source, it might be downloading
        if (!playerStore.isLoading) {
            playerStore.isPlaying = false
        }
    })
  } else {
    audioRef.value?.pause()
  }
})

// [New] Auto-play when audioUrl finally arrives after download
watch(() => playerStore.audioUrl, async (newUrl) => {
    if (newUrl && playerStore.currentSong) {
        console.log("[BottomPlayer] Audio URL updated, triggering auto-play")
        await nextTick()
        if (audioRef.value) {
            try {
                audioRef.value.load() // Explicitly load new source
                // Set playing but also explicitly wait and call play() to be sure
                playerStore.isPlaying = true
                await audioRef.value.play()
            } catch (e) {
                console.warn("[BottomPlayer] Auto-play after URL change failed:", e)
            }
        }
    }
})

// Quality helpers
const getQualityLabel = (q: any) => {
    if (!q) return ''
    const s = String(q).toUpperCase()
    // HR / Hi-Res
    if (s === 'HI-RES' || s === 'HR' || s.includes('24BIT') || s === 'MASTER') return 'HR'
    // HQ (High Quality Lossy)
    if (s === 'HQ' || s === '320K') return 'HQ'
    // SQ (Standard Lossless / High Quality) -> FLAC usually implies SQ or HR. Mapping FLAC to SQ for standard 16bit.
    if (s === 'FLAC' || s === 'SQ' || s === 'LOSSLESS') return 'SQ'
    // PQ (Standard Quality Lossy)
    if (s === 'PQ' || s === '128K') return 'PQ'
    
    return s // Return original if unknown
}

const getQualityClass = (q: any) => {
    const label = getQualityLabel(q)
    if (label === 'HR') return 'quality-gold' 
    if (label === 'SQ') return 'quality-green'
    if (label === 'HQ') return 'quality-blue'
    return 'quality-gray'
}

onMounted(() => {
  // 初始音量同步
  if (audioRef.value) audioRef.value.volume = playerStore.volume / 100
})


</script>

<template>
  <div class="bottom-player">
    <div class="player-container">
      <!-- 视效层 -->
      <!-- 视效层 (已移除以符合 Spotify 风格) -->
      <!-- 视效层 (已移除以符合 Spotify 风格) -->

      <!-- 左侧：歌曲信息 (30%) -->
      <div class="song-info">
        <div class="cover-art hover-scale clickable" @click="playerStore.toggleLyricsPanel()">
          <img :src="playerStore.currentSong?.cover || 'public/pwa-192x192.png'" alt="Cover" v-if="playerStore.currentSong">
          <div class="placeholder-cover" v-else>
            <n-icon :component="MusicalNotesOutline" />
          </div>
        </div>
        <div class="meta">
          <div class="title-container">
            <div class="title clickable" @click="playerStore.toggleLyricsPanel()">{{ playerStore.currentSong?.title || 'Music Monitor' }}</div>
            <!-- Quality Badge -->
            <div class="quality-wrapper">
                <n-tag size="small" :bordered="false" class="quality-tag" 
                       :class="getQualityClass(playerStore.currentSong?.quality)"
                       v-if="playerStore.currentSong?.quality">
                    {{ getQualityLabel(playerStore.currentSong.quality) }}
                </n-tag>
            </div>
          </div>
          <div class="artist" v-if="!playerStore.downloadMessage">{{ playerStore.currentSong?.artist || 'Ready to play' }}</div>
          <div class="download-status-text" v-else>{{ playerStore.downloadMessage }}</div>
        </div>
        <button class="fav-btn clickable apple-transition" v-if="playerStore.currentSong">
          <n-icon :component="playerStore.currentSong.is_favorite ? Heart : HeartOutline" />
        </button>
      </div>

      <!-- 中间：核心控制 (绝对居中) -->
      <div class="player-controls">
        <div class="control-buttons">
          <button class="icon-btn clickable" @click="playerStore.playPrev" :disabled="!playerStore.currentSong">
            <n-icon :component="PlaySkipBackSharp" />
          </button>
          <button class="play-btn clickable hover-scale" @click="togglePlay" :disabled="!playerStore.currentSong">
            <n-icon :component="playerStore.isPlaying ? PauseSharp : PlaySharp" />
          </button>
          <button class="icon-btn clickable" @click="playerStore.playNext" :disabled="!playerStore.currentSong">
            <n-icon :component="PlaySkipForwardSharp" />
          </button>
        </div>
        <div class="progress-area">
          <span class="time">{{ formatTime(playerStore.currentTime) }}</span>
          <n-slider 
            v-model:value="playerStore.currentTime" 
            :max="playerStore.duration || 100" 
            :step="1"
            :tooltip="false"
            :disabled="!playerStore.currentSong"
            @update:value="(v) => audioRef!.currentTime = v"
          />
          <span class="time">{{ formatTime(playerStore.duration) }}</span>
        </div>
      </div>

      <!-- 右侧：歌词与功能 (30%) -->
      <div class="right-side-controls">
          <!-- 迷你歌词显示 -->
          <div class="mini-lyrics-container clickable" @click="playerStore.toggleLyricsPanel()" v-if="currentLyricText">
            <span class="mini-lyric-text">{{ currentLyricText }}</span>
          </div>
          <div class="mini-lyrics-container" v-else></div>

          <!-- 音量与功能 -->
          <div class="utility-controls">
            <button class="icon-btn clickable lyrics-btn" @click="playerStore.toggleLyricsPanel()" :class="{ active: playerStore.showLyricsPanel }">
                <span class="lyric-text-icon">词</span>
            </button>
            <div class="volume-control">
              <n-icon :component="playerStore.isMuted ? VolumeMuteOutline : VolumeMediumOutline" @click="playerStore.toggleMute" class="clickable"/>
              <n-slider 
                v-model:value="playerStore.volume" 
                :max="100" 
                :tooltip="false"
                @update:value="(v) => audioRef!.volume = v / 100"
                style="width: 80px"
              />
            </div>
          </div>
      </div>

      <audio 
        ref="audioRef" 
        :src="playerStore.audioUrl" 
        crossorigin="anonymous"
        @timeupdate="onTimeUpdate" 
        @loadedmetadata="onLoadedMetadata" 
        @ended="onEnded"
      ></audio>
    </div>
  </div>
</template>

<style scoped>
.bottom-player {
  height: var(--player-height);
  background-color: #000;
  border-top: 1px solid #282828;
  padding: 0 16px;
  display: flex;
  align-items: center;
}
.player-container { width: 100%; height: 100%; display: flex; align-items: center; justify-content: space-between; position: relative; }
/* .visualizer-canvas { ... } */

.song-info { display: flex; align-items: center; gap: 14px; width: 30%; z-index: 1; min-width: 180px; }
.player-controls { 
    position: absolute; 
    left: 50%; 
    top: 50%; 
    transform: translate(-50%, -50%); 
    width: 40%; 
    max-width: 722px; 
    display: flex; 
    flex-direction: column; 
    align-items: center; 
    justify-content: center; 
    gap: 8px; /* Reduced gap */
}
.right-side-controls {
    display: flex;
    align-items: center;
    width: 30%;
    justify-content: flex-end;
    gap: 16px;
    z-index: 1;
    min-width: 180px;
}


.song-info { display: flex; align-items: center; gap: 14px; width: 30%; z-index: 1; min-width: 180px; }
.cover-art { width: 56px; height: 56px; border-radius: 4px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
.cover-art img { width: 100%; height: 100%; object-fit: cover; }
.title-container { display: flex; align-items: center; gap: 8px; }
.title { font-size: 14px; font-weight: 600; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; cursor: default; }

/* Mini Lyrics */
.mini-lyrics-container {
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    margin: 0 16px;
    overflow: hidden;
    position: relative;
    z-index: 2;
    min-width: 0; /* Important for flex child truncation */
}

.mini-lyric-text {
    font-size: 14px;
    color: var(--sp-green); /* Always Green */
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
    text-shadow: 0 1px 2px rgba(0,0,0,0.8);
    font-weight: 500;
    transition: color 0.3s;
    cursor: pointer;
}

.mini-lyrics-container:hover .mini-lyric-text {
    /* No underline */
    opacity: 1;
    text-decoration: none;
}
/* Modern Pill Style (Option B) */
.quality-tag { 
    font-size: 10px; 
    height: 18px; /* Slightly taller for pill shape */
    line-height: 16px; 
    padding: 0 6px; 
    background-color: rgba(255, 255, 255, 0.1);
    color: #fff; 
    font-weight: 700;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px; /* Rounded corners for pill effect */
    margin-left: 8px;
    display: inline-flex;
    align-items: center;
    backdrop-filter: blur(4px);
    letter-spacing: 0.5px;
}

/* Quality Colors - Modern Pill Variant */
.quality-gold { 
    color: #FFD700; 
    border: 1px solid rgba(255, 215, 0, 0.3); 
    background: rgba(255, 215, 0, 0.15); 
}
.quality-green { 
    color: #1DB954; 
    border: 1px solid rgba(29, 185, 84, 0.3); 
    background: rgba(29, 185, 84, 0.15); 
}
.quality-blue { 
    color: #4facfe; 
    border: 1px solid rgba(79, 172, 254, 0.3); 
    background: rgba(79, 172, 254, 0.15); 
}
.quality-gray { 
    color: #aaa; 
    border: 1px solid rgba(255, 255, 255, 0.2); 
    background: rgba(255, 255, 255, 0.05); 
}
.artist { font-size: 12px; color: var(--text-secondary); }

.quality-wrapper {
    display: inline-flex;
    align-items: center;
    cursor: default; /* Changed from help to default to avoid confusion */
}

/* Mini EQ Animation */
.mini-eq { display: flex; align-items: flex-end; gap: 2px; height: 12px; width: 14px; margin-bottom: 2px; }
.eq-bar { width: 2px; height: 100%; background: var(--sp-green); border-radius: 1px; animation: eq-pulse 0.6s ease-in-out infinite alternate; }
.eq-bar:nth-child(1) { animation-duration: 0.4s; }
.eq-bar:nth-child(2) { animation-duration: 0.7s; }
.eq-bar:nth-child(3) { animation-duration: 0.5s; }
.eq-bar:nth-child(4) { animation-duration: 0.6s; }

@keyframes eq-pulse {
  0% { height: 20%; }
  100% { height: 100%; }
}

.fav-btn { background: none; border: none; font-size: 20px; color: var(--sp-green); opacity: 0.8; }
.fav-btn:hover { opacity: 1; transform: scale(1.1); }

.player-controls { flex: 1; max-width: 600px; display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 1; }
.control-buttons { display: flex; align-items: center; gap: 24px; }
.icon-btn { background: none; border: none; font-size: 20px; color: var(--text-secondary); }
.icon-btn:hover { color: #fff; }
.lyrics-btn { color: var(--sp-green) !important; opacity: 0.7; }
.lyrics-btn.active { opacity: 1; }
.lyric-text-icon { font-size: 16px; font-weight: 800; border: 2px solid currentColor; border-radius: 4px; padding: 0 3px; line-height: 1.2; display: inline-block; transform: scale(0.8); }

.play-btn { 
  background: #fff; 
  color: #000; 
  width: 40px; /* Bigger play button */
  height: 40px; 
  border-radius: 50%; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  border: none;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.play-btn:hover {
  transform: scale(1.08); /* More dynamic hover */
}
.play-btn .n-icon {
  font-size: 24px;
}

.progress-area { width: 100%; display: flex; align-items: center; gap: 10px; }
.time { font-size: 11px; color: var(--text-secondary); min-width: 32px; }

.time { font-size: 11px; color: var(--text-secondary); min-width: 32px; }

.utility-controls { width: 30%; display: flex; justify-content: flex-end; align-items: center; z-index: 1; gap: 16px; }
.volume-control { display: flex; align-items: center; gap: 12px; width: 120px; }

:deep(.n-slider-rail) { 
  height: 4px; 
  border-radius: 2px; 
  background-color: hsla(0,0%,100%,.3) !important; /* Spotify-style rail color */
}
:deep(.n-slider-rail__fill) { 
  background-color: #fff !important; /* White progress on hover or default? Spotify uses green on hover, gray default. Let's stick to green for branding here. */
}
.progress-area:hover :deep(.n-slider-rail__fill) {
    background-color: var(--sp-green) !important;
}
:deep(.n-slider-handle) { 
  width: 12px; 
  height: 12px; 
  opacity: 0; /* Hide handle by default */
  transition: opacity 0.2s;
  background-color: #fff !important;
}
.progress-area:hover :deep(.n-slider-handle) {
  opacity: 1; /* Show handle on hover */
}

.placeholder-cover {
  width: 100%; height: 100%;
  background: #282828;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #555;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.download-status-text {
  font-size: 11px;
  color: var(--sp-green);
  font-weight: 500;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}
</style>


