<template>
  <Transition name="slide-left">
    <div v-if="playerStore.showLyricsPanel" class="lyrics-panel">
      <div class="lyrics-header">
        <h3>歌词</h3>
        <button class="close-btn" @click="playerStore.toggleLyricsPanel()">
          <n-icon :component="CloseOutline" />
        </button>
      </div>
      
      <div class="lyrics-content" ref="lyricsContainer">
        <div v-if="playerStore.lyrics.length === 0" class="no-lyrics">
          <p>暂无歌词 / 纯音乐</p>
        </div>
        <div v-else class="lyrics-list">
          <div
            v-for="(line, index) in playerStore.lyrics"
            :key="index"
            class="lyric-line"
            :class="{ active: index === playerStore.currentLyricIndex }"
            :ref="(el) => { if (index === playerStore.currentLyricIndex) activeLyricRef = el }"
          >
            {{ line.text }}
          </div>
          <!-- Spacer for bottom padding -->
          <div class="lyrics-spacer"></div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { usePlayerStore } from '@/stores/player'
import { NIcon } from 'naive-ui'
import { CloseOutline } from '@vicons/ionicons5'

const playerStore = usePlayerStore()
const lyricsContainer = ref<HTMLElement | null>(null)
const activeLyricRef = ref<any>(null)

// Auto-scroll logic
watch(() => playerStore.currentLyricIndex, (newIdx) => {
    if (newIdx >= 0) {
        nextTick(() => {
            if (activeLyricRef.value) {
                activeLyricRef.value.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                })
            }
        })
    }
})

// Scroll when panel opens
watch(() => playerStore.showLyricsPanel, (show) => {
    if (show) {
        nextTick(() => {
            if (activeLyricRef.value) {
                activeLyricRef.value.scrollIntoView({ behavior: 'auto', block: 'center' })
            }
        })
    }
})
</script>

<style scoped>
.lyrics-panel {
  position: fixed;
  right: 0;
  top: 0;
  bottom: var(--player-height); /* 使用全局变量 */
  width: 400px;
  background: rgba(18, 18, 18, 0.95);
  backdrop-filter: blur(20px);
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 5500; /* Sidebar: 5000, Player: 6000. Lyrics should be below Player but above content */
  display: flex;
  flex-direction: column;
}

.lyrics-header {
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.lyrics-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.lyrics-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.no-lyrics {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
  font-size: 14px;
}

.lyrics-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 40px 0; /* Add top/bottom padding for better center effect */
}

.lyric-line {
  color: rgba(255, 255, 255, 0.4); /* Dim inactive lyrics */
  font-size: 20px;
  font-weight: 700;
  line-height: 1.4;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 12px 0;
  cursor: default;
}

.lyric-line.active {
  color: #FFFFFF;
  font-size: 28px; /* Prominent active line */
  transform: scale(1.05);
  transform-origin: left;
}

.lyrics-spacer {
    height: 300px;
}

/* 滑入滑出动画 */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: transform 0.3s ease;
}

.slide-left-enter-from {
  transform: translateX(100%);
}

.slide-left-leave-to {
  transform: translateX(100%);
}
</style>
