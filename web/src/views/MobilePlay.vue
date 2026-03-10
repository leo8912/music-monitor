<script setup lang="ts">
/**
 * 移动端极简播放页面 - 专为企业微信通知设计
 * 支持签名认证，无需登录即可播放
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { PlaySharp, PauseSharp, MusicalNotesOutline } from '@vicons/ionicons5'
import { NIcon, NSpin } from 'naive-ui'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const song = ref<any>(null)
const isPlaying = ref(false)
const audioRef = ref<HTMLAudioElement | null>(null)
const progress = ref(0)

// 获取元数据
const fetchMetadata = async () => {
    const { id, sign, expires } = route.query
    if (!id || !sign || !expires) {
        error.value = '链接参数不完整'
        loading.value = false
        return
    }

    try {
        const resp = await axios.get('/api/mobile/metadata', {
            params: { id, sign, expires }
        })
        song.value = resp.data
        loading.value = false
        
        // 尝试自动播放 (受限于浏览器策略，可能失败)
        setTimeout(() => {
            if (audioRef.value) {
                audioRef.value.play().then(() => {
                    isPlaying.value = true
                }).catch(() => {
                    console.log('Autoplay blocked')
                })
            }
        }, 500)
    } catch (e: any) {
        error.value = e.response?.data?.detail || '链接已失效或认证失败'
        loading.value = false
    }
}

const togglePlay = () => {
    if (!audioRef.value) return
    if (isPlaying.value) {
        audioRef.value.pause()
    } else {
        audioRef.value.play()
    }
    isPlaying.value = !isPlaying.value
}

const onTimeUpdate = () => {
    if (audioRef.value) {
        progress.value = (audioRef.value.currentTime / audioRef.value.duration) * 100
    }
}

onMounted(() => {
    fetchMetadata()
})

onUnmounted(() => {
    if (audioRef.value) {
        audioRef.value.pause()
    }
})
</script>

<template>
  <div class="mobile-play-page">
    <div v-if="loading" class="state-container">
        <n-spin size="large" description="正在准备音乐..." />
    </div>

    <div v-else-if="error" class="state-container error">
        <div class="error-icon">❌</div>
        <div class="error-text">{{ error }}</div>
    </div>

    <div v-else class="player-container">
        <!-- Background Blur -->
        <div class="bg-blur" :style="{ backgroundImage: `url(${song.cover})` }"></div>
        <div class="overlay"></div>

        <div class="content">
            <div class="cover-section">
                <div class="cover-card">
                    <img :src="song.cover" v-if="song.cover" alt="Cover">
                    <div class="placeholder" v-else>
                        <n-icon :component="MusicalNotesOutline" size="100" />
                    </div>
                </div>
            </div>

            <div class="info-section">
                <h1 class="song-title">{{ song.title }}</h1>
                <p class="song-artist">{{ song.artist }}</p>
                <p class="song-album" v-if="song.album">{{ song.album }}</p>
            </div>

            <div class="controls-section">
                <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: progress + '%' }"></div>
                </div>
                
                <button class="main-play-btn" @click="togglePlay">
                    <n-icon :component="isPlaying ? PauseSharp : PlaySharp" />
                </button>
            </div>

            <div class="footer">
                <p>Music Monitor • 极简播放</p>
            </div>
        </div>

        <audio 
            ref="audioRef" 
            :src="song.audio_url" 
            @timeupdate="onTimeUpdate"
            @ended="isPlaying = false"
        ></audio>
    </div>
  </div>
</template>

<style scoped>
.mobile-play-page {
    width: 100vw;
    height: 100vh;
    background: #000;
    color: #fff;
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.state-container {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
}

.error-text { color: #ff4d4f; font-size: 16px; text-align: center; padding: 0 40px; }

.player-container {
    position: relative;
    width: 100%;
    height: 100%;
}

.bg-blur {
    position: absolute;
    inset: -20px;
    background-size: cover;
    background-position: center;
    filter: blur(40px) brightness(0.4);
    z-index: 0;
}

.overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.8));
    z-index: 1;
}

.content {
    position: relative;
    z-index: 2;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 60px 20px;
    justify-content: space-between;
}

.cover-section {
    width: 100%;
    display: flex;
    justify-content: center;
}

.cover-card {
    width: 260px;
    height: 260px;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 20px 40px rgba(0,0,0,0.6);
}

.cover-card img { width: 100%; height: 100%; object-fit: cover; }

.info-section {
    text-align: center;
    margin-top: 20px;
}

.song-title { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
.song-artist { font-size: 18px; color: rgba(255,255,255,0.7); }
.song-album { font-size: 14px; color: rgba(255,255,255,0.5); margin-top: 4px; }

.controls-section {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 30px;
}

.progress-bar {
    width: 80%;
    height: 4px;
    background: rgba(255,255,255,0.2);
    border-radius: 2px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: #1DB954;
    transition: width 0.1s linear;
}

.main-play-btn {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: #fff;
    color: #000;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
}

.footer {
    font-size: 12px;
    color: rgba(255,255,255,0.3);
}
</style>
