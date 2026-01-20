<template>
  <div class="am-player">
    <!-- 动态模糊背景 -->
    <div class="am-bg-layer" :style="{ backgroundImage: `url(${coverUrl})` }"></div>
    <div class="am-bg-overlay"></div>

    <div class="am-content" v-if="meta">
        <!-- 顶部把手 (装饰 + 切换触发区) -->
        <div class="am-header-bar" @click="showLyrics = !showLyrics">
            <div class="am-handle"></div>
        </div>

        <!-- 主内容区域 -->
        <div class="am-main-body">
            <!-- 封面区域 -->
            <div class="am-artwork-section" 
                 :class="{ 'collapsed': showLyrics }"
                 @click="showLyrics = true">
                <div class="am-artwork-wrapper" :class="{ 'pumping': isPlaying && !showLyrics }">
                    <img :src="coverUrl" class="am-artwork-img" @error="onCoverError" />
                    <div class="am-artwork-placeholder" v-if="coverError">
                        🎵
                    </div>
                </div>
            </div>

            <!-- 歌词区域 -->
            <!-- 点击非歌词区域可以退出歌词模式 -->
            <div class="am-lyrics-section" 
                 :class="{ 'active': showLyrics }" 
                 @click.self="showLyrics = false">
                <div class="am-lyrics-scroll" ref="lyricsContainer">
                     <p v-if="!parsedLyrics.length" class="am-no-lyrics" @click="showLyrics = false">
                        暂无歌词<br><span style="font-size:12px;opacity:0.6">(点击返回)</span>
                     </p>
                     <p 
                        v-for="(line, idx) in parsedLyrics" 
                        :key="idx" 
                        class="am-lrc-line"
                        :class="{ 'active': currentLine === idx, 'blur': currentLine !== idx }"
                        @click.stop="seekTo(line.time)"
                     >
                        {{ line.text }}
                     </p>
                     <div style="height: 50vh;" @click="showLyrics = false"></div> 
                </div>
            </div>

            <!-- 信息与控制区域 -->
            <div class="am-player-controls" :class="{ 'dimmed': showLyrics }">
                <!-- 标题与收藏 -->
                <div class="am-meta-row">
                    <div class="am-titles">
                        <div class="am-song-title">{{ meta.title }}</div>
                        <div class="am-artist-name">{{ meta.artist }}</div>
                    </div>
                    <button class="am-btn-icon am-btn-fav" @click="toggleFavorite">
                         <svg v-if="meta.is_favorite" viewBox="0 0 24 24" fill="#FF2D55" width="28" height="28"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
                         <svg v-else viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="2" width="28" height="28"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
                    </button>
                </div>

                <!-- 进度条 -->
                <div class="am-progress-section">
                    <input 
                        type="range" 
                        class="am-slider" 
                        :value="currentTime" 
                        :max="duration || 1" 
                        @input="onSeekInput"
                        @change="onSeekChange"
                        :style="sliderStyle"
                    />
                    <div class="am-time-labels">
                        <span>{{ formatTime(displayTime) }}</span>
                        <span>{{ formatTime(duration) }}</span>
                    </div>
                </div>

                <!-- 播放控制 -->
                <div class="am-transport-controls">
                    <button class="am-btn-transport sm" @click="seekBy(-10)">
                        <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32"><path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/></svg>
                    </button>
                    
                    <button class="am-btn-play" @click="togglePlay">
                         <svg v-if="isPlaying" viewBox="0 0 24 24" fill="currentColor" width="56" height="56"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                         <svg v-else viewBox="0 0 24 24" fill="currentColor" width="56" height="56"><path d="M8 5v14l11-7z"/></svg>
                    </button>
                    
                    <button class="am-btn-transport sm" @click="seekBy(10)">
                        <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32"><path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/></svg>
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <div v-if="loading" class="am-loading"><div class="am-spinner"></div></div>
    <div v-if="error" class="am-error"><p>{{ error }}</p></div>

    <audio ref="audioRef" :src="meta?.audio_url" @timeupdate="onTimeUpdate" @loadedmetadata="onLoadedMetadata" @ended="onEnded"></audio>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const meta = ref(null)
const error = ref(null)
const loading = ref(true)
const coverError = ref(false)

const audioRef = ref(null)
const isPlaying = ref(false)
const duration = ref(0)
const currentTime = ref(0)
const isSeeking = ref(false)
const seekValue = ref(0)

const showLyrics = ref(false)
const parsedLyrics = ref([])
const currentLine = ref(-1)
const lyricsContainer = ref(null)

const coverUrl = computed(() => {
    if (coverError.value || !meta.value?.cover) return '/default_cover.jpg'
    return meta.value.cover
})

const sliderStyle = computed(() => {
    const val = isSeeking.value ? seekValue.value : currentTime.value
    const max = duration.value || 1
    const p = (val / max) * 100
    // Use percent for gradient
    const pct = Math.min(Math.max(p, 0), 100)
    return {
        background: `linear-gradient(to right, rgba(255,255,255,0.9) ${pct}%, rgba(255,255,255,0.2) ${pct}%)`
    }
})

const displayTime = computed(() => isSeeking.value ? seekValue.value : currentTime.value)

const togglePlay = () => {
    if(!audioRef.value) return
    if(isPlaying.value) audioRef.value.pause()
    else audioRef.value.play()
    isPlaying.value = !isPlaying.value
}

const seekBy = (delta) => {
    if(!audioRef.value) return
    audioRef.value.currentTime = Math.min(Math.max(audioRef.value.currentTime + delta, 0), duration.value)
}

const seekTo = (time) => {
    if(!audioRef.value) return
    audioRef.value.currentTime = time
    // Optional: auto play if paused
    if(!isPlaying.value) {
        audioRef.value.play()
        isPlaying.value = true
    }
}

const onSeekInput = (e) => {
    isSeeking.value = true
    seekValue.value = Number(e.target.value)
}
const onSeekChange = (e) => {
    if(!audioRef.value) return
    audioRef.value.currentTime = Number(e.target.value)
    isSeeking.value = false
}

const onTimeUpdate = (e) => {
    if(!isSeeking.value) currentTime.value = e.target.currentTime
    
     if (parsedLyrics.value.length) {
       // slightly safer lookup
       const t = e.target.currentTime
       let idx = -1
       for(let i=0; i<parsedLyrics.value.length; i++) {
           if(parsedLyrics.value[i].time > t) {
               idx = i - 1
               break
           }
       }
       if(idx === -1 && t >= parsedLyrics.value[parsedLyrics.value.length-1].time) {
           idx = parsedLyrics.value.length - 1
       }
       
       if(idx >= 0 && currentLine.value !== idx) {
           currentLine.value = idx
           scrollToCurrentLyric()
       }
   }
}

const scrollToCurrentLyric = () => {
    if(showLyrics.value && lyricsContainer.value && currentLine.value >= 0) {
        const el = lyricsContainer.value.children[currentLine.value]
        if(el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
}

const onLoadedMetadata = (e) => {
    duration.value = e.target.duration
    loading.value = false
    audioRef.value.play().then(() => isPlaying.value = true).catch(() => {})
}

const onEnded = () => { isPlaying.value = false }
const onCoverError = () => { coverError.value = true }
const formatTime = (s) => {
    if(!s || isNaN(s)) return "0:00"
    const m = Math.floor(s/60)
    const sec = Math.floor(s%60)
    return `${m}:${sec.toString().padStart(2,'0')}`
}

const parseLrc = (lrc) => {
    if(!lrc) return []
    const lines = lrc.split('\n')
    const res = []
    const re = /\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)/
    lines.forEach(line => {
        const m = re.exec(line)
        if(m) {
            const t = parseInt(m[1])*60 + parseInt(m[2]) + parseInt(m[3])/1000
            res.push({time: t, text: m[4].trim()})
        }
    })
    return res
}

const toggleFavorite = async () => {
    if(!meta.value) return
    meta.value.is_favorite = !meta.value.is_favorite // optimistic update
    try {
        await axios.post('/api/favorites/toggle', {
            source: meta.value.source,
            song_id: meta.value.id,
            title: meta.value.title,
            artist: meta.value.artist,
            pic_url: meta.value.cover
        })
    } catch(e) { /* ignore */ }
}

onMounted(async () => {
    const { id, sign, expires } = route.query
    if(!id) { error.value = "无效链接"; loading.value = false; return }
    try {
        const res = await axios.get(`/api/mobile/metadata?id=${id}&sign=${sign}&expires=${expires}`)
        meta.value = res.data
        if(res.data.lyrics) parsedLyrics.value = parseLrc(res.data.lyrics)
        loading.value = false
    } catch(e) {
        error.value = "加载失败: " + e.message
        loading.value = false
    }
})

watch(showLyrics, (v) => { if(v) setTimeout(scrollToCurrentLyric, 100) })
</script>

<style scoped>
/* Apple Music Style Theme */
.am-player {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    overflow: hidden;
    font-family: -apple-system, "SF Pro Display", "PingFang SC", sans-serif;
    color: white;
    background: #000;
}
.am-bg-layer {
    position: absolute; width: 100%; height: 100%;
    background-size: cover; background-position: center;
    filter: blur(80px) saturate(180%);
    opacity: 0.6;
    transform: scale(1.2);
    z-index: 1;
}
.am-bg-overlay {
    position: absolute; width: 100%; height: 100%;
    background: linear-gradient(to bottom, rgba(0,0,0,0.2), rgba(0,0,0,0.6));
    z-index: 2;
}

.am-content {
    position: relative; z-index: 10;
    height: 100%; display: flex; flex-direction: column;
}

.am-header-bar {
    height: 40px; display: flex; justify-content: center; align-items: center;
    padding-top: 10px; flex-shrink: 0; cursor: pointer;
}
.am-handle {
    width: 36px; height: 5px; background: rgba(255,255,255,0.2); border-radius: 3px;
}

.am-main-body {
    flex: 1;
    display: flex; flex-direction: column;
    padding: 0 32px 48px;
    overflow: hidden;
    position: relative;
}

/* Artwork */
.am-artwork-section {
    flex: 1; 
    display: flex; align-items: center; justify-content: center;
    transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
    min-height: 0;
    cursor: pointer;
}
.am-artwork-section.collapsed {
    flex: 0 0 60px;
    opacity: 1; /* Changed from 0 to allow visibility of tiny icon if desired, but Apple Music hides it mostly. Actually collapsed usually means it goes to top. Let's keep it minimal. */
    opacity: 0; pointer-events: none;
    transform: scale(0.8);
    height: 0; margin: 0; overflow: hidden;
}

.am-artwork-wrapper {
    width: 80vw;
    height: 80vw;
    max-width: 320px; max-height: 320px;
    border-radius: 12px;
    box-shadow: 0 20px 40px -10px rgba(0,0,0,0.5);
    transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
    transform: scale(0.85); 
    position: relative;
    overflow: hidden;
    background: #222;
}
.am-artwork-wrapper.pumping {
    transform: scale(1);
    box-shadow: 0 24px 50px -12px rgba(0,0,0,0.6);
}
.am-artwork-img { width: 100%; height: 100%; object-fit: cover; }
.am-artwork-placeholder {
    position: absolute; top:0; left:0; width:100%; height:100%;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #444, #222);
    font-size: 64px;
}

/* Lyrics */
.am-lyrics-section {
    position: absolute; top: 0; left: 0; width: 100%; bottom: 180px; /* Leave space for controls */
    padding: 20px 32px 0;
    overflow: hidden;
    opacity: 0; pointer-events: none;
    transition: all 0.4s ease;
    z-index: 5;
    background: transparent;
}
.am-lyrics-section.active {
    opacity: 1; pointer-events: auto;
}
.am-lyrics-scroll {
    height: 100%;
    overflow-y: scroll;
    -webkit-overflow-scrolling: touch;
    mask-image: linear-gradient(to bottom, transparent, black 10%, black 90%, transparent);
}
.am-lyrics-scroll::-webkit-scrollbar { display: none; }

.am-lrc-line {
    font-size: 26px; line-height: 1.5;
    font-weight: 700;
    margin: 32px 0;
    color: rgba(255,255,255,0.4);
    transition: all 0.3s ease;
    cursor: pointer;
    text-align: left;
    transform-origin: left center;
}
.am-lrc-line.active {
    color: #fff;
    filter: blur(0);
    transform: scale(1.05);
}
.am-lrc-line.blur {
    filter: blur(0.8px);
}
.am-no-lyrics {
    margin-top: 100px; text-align: center; color: rgba(255,255,255,0.5);
    font-size: 18px; line-height: 1.6;
}

/* Controls */
.am-player-controls {
    flex-shrink: 0;
    margin-top: auto;
    transition: opacity 0.3s;
    background: transparent; /* Ensure no blocking */
    position: relative; z-index: 20;
}
.am-player-controls.dimmed {
    /* Optional: dim controls slightly in lyrics mode? Apple Music keeps them bright. */
}

.am-meta-row {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 24px;
}
.am-titles { flex: 1; padding-right: 16px; text-align: left; }
.am-song-title {
    font-size: 22px; font-weight: 700; margin-bottom: 4px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.am-artist-name {
    font-size: 18px; color: rgba(255,255,255,0.6);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.am-btn-fav {
    padding: 8px; margin-right: -8px; opacity: 0.8;
    background: none; border: none; cursor: pointer;
}
.am-btn-fav:active { transform: scale(0.9); opacity: 1; }

.am-progress-section { margin-bottom: 32px; position: relative; }
.am-slider {
    width: 100%; -webkit-appearance: none; height: 4px; background: rgba(255,255,255,0.2);
    border-radius: 2px; outline: none; display: block;
    cursor: pointer;
    position: relative; z-index: 30; /* Ensure clickable */
}
.am-slider::-webkit-slider-thumb {
    -webkit-appearance: none; width: 22px; height: 22px; border-radius: 50%;
    background: #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    transform: scale(0.4); transition: transform 0.2s;
    margin-top: -9px; /* center vertically if needed for cross-browser but usually flex handles it */
}
.am-slider:active::-webkit-slider-thumb { transform: scale(1); }

/* Custom Track Logic for input[type=range] varies by browser. */
/* Just rely on background gradient for track fill */

.am-time-labels {
    display: flex; justify-content: space-between;
    margin-top: 8px; font-size: 12px; color: rgba(255,255,255,0.4); font-weight: 500;
}

.am-transport-controls {
    display: flex; justify-content: center; align-items: center;
    gap: 40px; margin-bottom: 10px;
}
.am-btn-transport {
    background: none; border: none; color: #fff; opacity: 0.9; cursor: pointer; padding: 0;
}
.am-btn-transport:active { opacity: 0.5; }
.am-btn-play {
    background: none; border: none; color: #fff; cursor: pointer; padding: 0;
    transition: transform 0.1s;
}
.am-btn-play:active { transform: scale(0.9); }

.am-loading, .am-error {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    z-index: 100; color: #fff; background: #000;
}
.am-spinner {
    width: 32px; height: 32px; border: 3px solid rgba(255,255,255,0.3); border-top-color: #fff;
    border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
