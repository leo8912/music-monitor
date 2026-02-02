<template>
  <Transition name="slide-left">
    <div v-if="playerStore.showLyricsPanel" class="lyrics-panel">
      <div class="lyrics-header">
        <h3>歌词</h3>
        <button class="close-btn" @click="playerStore.toggleLyricsPanel()">
          <n-icon :component="CloseOutline" />
        </button>
      </div>
      
      <div class="lyrics-content">
        <div v-if="playerStore.lyrics.length === 0" class="no-lyrics">
          <p>暂无歌词 / 纯音乐</p>
        </div>
        <div v-else class="lyrics-list">
          <div
            v-for="(line, index) in playerStore.lyrics"
            :key="index"
            class="lyric-line"
            :class="{ active: index === playerStore.currentLyricIndex }"
          >
            {{ line.text }}
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { usePlayerStore } from '@/stores/player'
import { NIcon } from 'naive-ui'
import { CloseOutline } from '@vicons/ionicons5'

const playerStore = usePlayerStore()
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
  gap: 16px;
}

.lyric-line {
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.6;
  transition: all 0.3s;
  padding: 8px 12px;
  border-radius: 4px;
}

.lyric-line.active {
  color: var(--sp-green);
  font-weight: 600;
  background: rgba(29, 185, 84, 0.1);
  transform: scale(1.02);
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
