<template>
  <div class="mobile-player" v-if="meta">
    <!-- Background Blur -->
    <div class="bg-layer" :style="{ backgroundImage: `url(${meta.cover || '/default_cover.jpg'})` }"></div>
    <div class="bg-overlay"></div>

    <div class="player-content">
      <!-- Header -->
      <div class="header">
        <div class="pill">Music Monitor</div>
      </div>

      <!-- Main Visual -->
      <div class="visual-container" @click="toggleLyrics">
        <!-- Cover Art -->
        <div class="cover-art" :class="{ 'playing': isPlaying, 'hidden': showLyrics }">
          <img :src="meta.cover || '/default_cover.jpg'" alt="Cover" />
        </div>
        
        <!-- Lyrics View -->
        <div class="lyrics-view" :class="{ 'visible': showLyrics }">
           <div class="lyrics-inner" ref="lyricsContainer">
              <p v-if="!parsedLyrics.length" class="no-lyrics">暂无歌词</p>
              <p 
                v-for="(line, idx) in parsedLyrics" 
                :key="idx" 
                :class="{ 'active': currentLine === idx }"
                class="lyric-line"
                @click="seekTo(line.time)"
              >
                {{ line.text }}
              </p>
           </div>
        </div>
      </div>

      <!-- Info & Controls -->
      <div class="controls-container">
        <div class="track-info">
          <h1 class="title">{{ meta.title }}</h1>
          <h2 class="artist">{{ meta.artist }}</h2>
        </div>

        <!-- Slider -->
        <div class="progress-bar">
           <span class="time">{{ formatTime(currentTime) }}</span>
           <input 
             type="range" 
             min="0" 
             :max="duration" 
             v-model="seekTime"
             @input="isSeeking = true"
             @change="onSeekParams"
             class="slider" 
             :style="sliderStyle"
           />
           <span class="time">{{ formatTime(duration) }}</span>
        </div>

        <!-- Main Buttons -->
        <div class="buttons">
           <button class="btn-control" @click="seekBy(-10)">
             <svg viewBox="0 0 24 24" width="28" height="28" stroke="currentColor" stroke-width="2" fill="none"><path d="M11 19l-9-7 9-7v14zM22 19l-9-7 9-7v14z"/></svg>
           </button>
           
           <button class="btn-play" @click="togglePlay">
             <svg v-if="isPlaying" viewBox="0 0 24 24" width="32" height="32" fill="currentColor"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>
             <svg v-else viewBox="0 0 24 24" width="32" height="32" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
           </button>
           
           <button class="btn-control" @click="seekBy(10)">
             <svg viewBox="0 0 24 24" width="28" height="28" stroke="currentColor" stroke-width="2" fill="none"><path d="M13 19l9-7-9-7v14zM2 19l9-7-9-7v14z"/></svg>
           </button>
        </div>
      </div>
    </div>

    <audio 
      ref="audioRef" 
      :src="meta.audio_url" 
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoadedMetadata"
      @ended="onEnded"
    ></audio>
  </div>
  
  <div v-else-if="error" class="error-screen">
      <div class="error-icon">⚠️</div>
      <p>{{ error }}</p>
  </div>
  
  <div v-else class="loading-screen">
      <div class="spinner"></div>
      <p>正在载入...</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const meta = ref(null)
const error = ref(null)
const audioRef = ref(null)

const isPlaying = ref(false)
const duration = ref(0)
const currentTime = ref(0)
const seekTime = ref(0)
const isSeeking = ref(false)

const showLyrics = ref(false)
const parsedLyrics = ref([])
const currentLine = ref(-1)
const lyricsContainer = ref(null)

const toggleLyrics = () => { showLyrics.value = !showLyrics.value }

const togglePlay = () => {
  if (audioRef.value) {
    if (isPlaying.value) audioRef.value.pause()
    else audioRef.value.play()
    isPlaying.value = !isPlaying.value
  }
}

const seekBy = (sec) => {
   if (audioRef.value) audioRef.value.currentTime += sec
}

const onSeekParams = (e) => {
   if (audioRef.value) {
       audioRef.value.currentTime = e.target.value
       isSeeking.value = false
   }
}

const onTimeUpdate = (e) => {
   currentTime.value = e.target.currentTime
   if (!isSeeking.value) seekTime.value = currentTime.value
   
   // Sync Lyrics
   if (parsedLyrics.value.length) {
       let idx = parsedLyrics.value.findIndex(l => l.time > currentTime.value)
       if (idx === -1) idx = parsedLyrics.value.length
       currentLine.value = idx - 1
       
       // Scroll
       if (currentLine.value >= 0 && lyricsContainer.value && showLyrics.value) {
           const el = lyricsContainer.value.children[currentLine.value]
           if (el) {
               el.scrollIntoView({ behavior: "smooth", block: "center" })
           }
       }
   }
}

const onLoadedMetadata = (e) => {
    duration.value = e.target.duration
    isPlaying.value = true
    audioRef.value.play().catch(e => console.log("Autoplay blocked:", e))
}

const onEnded = () => {
    isPlaying.value = false
}

const formatTime = (s) => {
    if (!s) return "0:00"
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${sec.toString().padStart(2, '0')}`
}

const sliderStyle = computed(() => {
    const p = duration.value > 0 ? (seekTime.value / duration.value) * 100 : 0
    return {
        background: `linear-gradient(to right, #fff ${p}%, rgba(255,255,255,0.2) ${p}%)`
    }
})

// Parse Lyrics
const parseLrc = (lrc) => {
    if (!lrc) return []
    const lines = lrc.split('\n')
    const result = []
    const regex = /\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)/
    for (const line of lines) {
        const match = regex.exec(line)
        if (match) {
            const min = parseInt(match[1])
            const sec = parseInt(match[2])
            const ms = parseInt(match[3])
            const time = min * 60 + sec + ms / (match[3].length === 3 ? 1000 : 100)
            const text = match[4].trim()
            if (text) result.push({ time, text })
        }
    }
    return result
}

onMounted(async () => {
    const { id, sign, expires } = route.query
    if (!id || !sign || !expires) {
        error.value = "无效链接 (Missing parameters)"
        return
    }
    
    try {
        const res = await fetch(`/api/mobile/metadata?id=${id}&sign=${sign}&expires=${expires}`)
        if (!res.ok) {
             if (res.status === 403) throw new Error("链接已过期或签名无效")
             else throw new Error("获取数据失败")
        }
        const data = await res.json()
        meta.value = data
        parsedLyrics.value = parseLrc(data.lyrics)
        
        // Dynamic Title
        document.title = `${data.title} - ${data.artist}`
        
    } catch (e) {
        error.value = e.message
    }
})
</script>

<style scoped>
.mobile-player {
    position: fixed;
    top: 0; left: 0; width: 100%; height: 100%;
    color: white;
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.bg-layer {
    position: absolute;
    top: -10%; left: -10%; width: 120%; height: 120%;
    background-size: cover;
    background-position: center;
    filter: blur(50px) brightness(0.6);
    z-index: -2;
}
.bg-overlay {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.2);
    z-index: -1;
}

.player-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 24px;
    box-sizing: border-box;
}

.header {
    height: 60px;
    display: flex;
    justify-content: center;
    align-items: center;
}
.pill {
    background: rgba(255,255,255,0.2);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    color: rgba(255,255,255,0.8);
    backdrop-filter: blur(10px);
}

.visual-container {
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
    cursor: pointer;
}

.cover-art {
    width: 280px;
    height: 280px;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    transition: transform 0.5s ease, opacity 0.3s;
}
.cover-art.hidden {
    opacity: 0;
    transform: scale(0.9);
    pointer-events: none;
}
.cover-art img {
    width: 100%; height: 100%; object-fit: cover;
}

.lyrics-view {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    mask-image: linear-gradient(to bottom, transparent, black 15%, black 85%, transparent);
}
.lyrics-view.visible {
    opacity: 1;
    pointer-events: auto;
}
.lyrics-inner {
    width: 100%;
    max-height: 100%;
    overflow-y: auto;
    text-align: center;
    padding: 40px 0;
}
/* Hide scrollbar */
.lyrics-inner::-webkit-scrollbar { display: none; }

.lyric-line {
    font-size: 16px;
    color: rgba(255,255,255,0.5);
    margin: 16px 0;
    transition: all 0.3s;
    cursor: pointer;
}
.lyric-line.active {
    color: #fff;
    font-size: 20px;
    font-weight: bold;
    transform: scale(1.05);
}

.controls-container {
    margin-bottom: 40px;
}
.track-info {
    margin-bottom: 24px;
    text-align: left;
}
.title { font-size: 24px; margin: 0 0 8px 0; font-weight: 700; }
.artist { font-size: 16px; color: rgba(255,255,255,0.7); margin: 0; font-weight: 400; }

.progress-bar {
    display: flex;
    align-items: center;
    margin-bottom: 24px;
    font-size: 12px;
    color: rgba(255,255,255,0.6);
}
.slider {
    flex: 1;
    margin: 0 12px;
    -webkit-appearance: none;
    height: 4px;
    border-radius: 2px;
    background: rgba(255,255,255,0.2);
    outline: none;
}
.slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px; height: 16px;
    border-radius: 50%;
    background: #fff;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}

.buttons {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 40px;
}
.btn-play {
    width: 64px; height: 64px;
    border: none;
    border-radius: 50%;
    background: #fff;
    color: #000;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 0.1s;
}
.btn-play:active { transform: scale(0.95); }
.btn-control {
    background: none; border: none; color: #fff; cursor: pointer; opacity: 0.8;
}
.btn-control:active { opacity: 0.5; }

.error-screen, .loading-screen {
    height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #fff;
    background: #111;
}
.error-icon { font-size: 48px; margin-bottom: 16px; }
.spinner {
    width: 24px; height: 24px;
    border: 3px solid rgba(255,255,255,0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
