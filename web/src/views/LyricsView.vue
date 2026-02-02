<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { usePlayerStore } from '@/stores'
// @ts-ignore
import ColorThief from 'colorthief/dist/color-thief.mjs'
import { MusicalNotesOutline } from '@vicons/ionicons5'
import { NIcon } from 'naive-ui'

const playerStore = usePlayerStore()
const lyricContainer = ref<HTMLElement | null>(null)
const bgStyle = ref({})

// Color Thief Logic
const colorThief = new ColorThief()

const updateBackground = () => {
    if (!playerStore.currentSong?.cover) {
        bgStyle.value = { background: '#121212' }
        return
    }

    const img = new Image()
    img.crossOrigin = 'Anonymous'
    img.src = playerStore.currentSong.cover
    
    img.onload = () => {
        try {
            const palette = colorThief.getPalette(img, 3)
            if (palette && palette.length >= 2) {
                const c1 = palette[0]
                const c2 = palette[1]
                // 动态流光背景
                bgStyle.value = {
                    background: `linear-gradient(135deg, rgb(${c1[0]},${c1[1]},${c1[2]}) 0%, rgb(${c2[0]},${c2[1]},${c2[2]}) 100%)`,
                    transition: 'background 1s ease'
                }
            }
        } catch (e) {
            console.warn('Color thief failed', e)
            bgStyle.value = { background: '#202020' }
        }
    }
}

watch(() => playerStore.currentSong?.cover, updateBackground, { immediate: true })

// Auto-scroll logic
watch(() => playerStore.currentLyricIndex, (index) => {
  if (index !== -1 && lyricContainer.value) {
    const activeLine = lyricContainer.value.children[index] as HTMLElement
    if (activeLine) {
      activeLine.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }
})
</script>

<template>
  <div class="lyrics-view" :style="bgStyle">
    <div class="glass-overlay"></div>
    
    <div class="content-wrapper">
        <!-- Left: Huge Cover Art & Info -->
        <div class="info-section">
            <div class="cover-container hover-scale">
                 <img :src="playerStore.currentSong?.cover || 'public/pwa-192x192.png'" v-if="playerStore.currentSong?.cover">
                 <div class="placeholder" v-else>
                    <n-icon :component="MusicalNotesOutline" size="80" />
                 </div>
            </div>
            
            <div class="meta-info">
                <div class="song-title">{{ playerStore.currentSong?.title || 'No Music Playing' }}</div>
                <div class="song-artist">{{ playerStore.currentSong?.artist || 'Unknown Artist' }}</div>
                <div class="song-album">{{ playerStore.currentSong?.album || '' }}</div>
                
                <div class="badges" v-if="playerStore.currentSong?.quality">
                    <span class="quality-badge">{{ playerStore.currentSong.quality }}</span>
                    <span class="source-badge">{{ playerStore.currentSong.source?.toUpperCase() }}</span>
                </div>
            </div>
        </div>

        <!-- Right: Scrolling Lyrics -->
        <div class="lyrics-section" ref="lyricContainer">
             <div v-if="playerStore.lyrics.length === 0" class="no-lyrics">
                <span>暂无歌词 /纯音乐</span>
             </div>
             <div 
                v-else
                v-for="(line, index) in playerStore.lyrics" 
                :key="index"
                class="lyric-line"
                :class="{ active: index === playerStore.currentLyricIndex }"
                @click="playerStore.seek(line.time)"
            >
                {{ line.text }}
            </div>
            <!-- Spacer -->
            <div style="height: 50vh"></div>
        </div>
    </div>
  </div>
</template>

<style scoped>
.lyrics-view {
    height: 100%;
    width: 100%;
    position: relative;
    overflow: hidden;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
}

.glass-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.3); /* Darken slightly */
    backdrop-filter: blur(60px) saturate(180%); /* Apple Music style heavy blur */
    z-index: 0;
}

.content-wrapper {
    position: relative;
    z-index: 1;
    display: flex;
    width: 90%;
    max-width: 1200px;
    height: 80%;
    gap: 60px;
}

/* Left Section */
.info-section {
    width: 45%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 32px;
}

.cover-container {
    width: 100%;
    aspect-ratio: 1/1;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 24px 48px rgba(0,0,0,0.5);
    background: #282828;
}
.cover-container img { width: 100%; height: 100%; object-fit: cover; }
.placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #666; }

.meta-info { display: flex; flex-direction: column; gap: 8px; }
.song-title { font-size: 32px; font-weight: 800; line-height: 1.2; }
.song-artist { font-size: 20px; color: rgba(255,255,255,0.8); font-weight: 500; }
.song-album { font-size: 16px; color: rgba(255,255,255,0.6); }

.badges { display: flex; gap: 8px; margin-top: 8px; }
.quality-badge, .source-badge {
    padding: 2px 6px;
    border: 1px solid rgba(255,255,255,0.4);
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    color: rgba(255,255,255,0.9);
    letter-spacing: 0.5px;
}
.quality-badge { border-color: #d4af37; color: #ffdb58; /* Goldish for Hi-Res */ }

/* Right Section: Lyrics */
.lyrics-section {
    flex: 1;
    height: 100%;
    overflow-y: auto;
    scrollbar-width: none;
    mask-image: linear-gradient(to bottom, transparent, black 15%, black 85%, transparent);
    padding: 60px 0;
}

.lyric-line {
    font-size: 24px;
    font-weight: 600;
    color: rgba(255,255,255,0.35);
    margin-bottom: 28px;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    transform-origin: left center;
    padding: 4px 16px;
    border-radius: 8px;
}

.lyric-line:hover {
    color: rgba(255,255,255,0.7);
    background: rgba(255,255,255,0.05); 
}

.lyric-line.active {
    font-size: 34px; /* Maginify active line */
    color: #fff;
    font-weight: 800;
    transform: scale(1.02);
    filter: drop-shadow(0 0 10px rgba(0,0,0,0.3));
}

.no-lyrics {
    height: 100%;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px; color: rgba(255,255,255,0.4);
}
</style>
