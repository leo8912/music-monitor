<script setup lang="ts">
/**
 * 移动端迷你播放器组件 - Spotify 风格
 */

import { computed } from 'vue'
import { usePlayerStore } from '@/stores'
import type { Song } from '@/types'

const props = defineProps<{
  song: Song
  isPlaying: boolean
  isLoading?: boolean
}>()

const emit = defineEmits<{
  (e: 'click'): void
  (e: 'toggle'): void
}>()

const playerStore = usePlayerStore()

const formatArtist = (artist: string | string[]) => {
  return Array.isArray(artist) ? artist.join(', ') : artist
}

// 模拟进度 (如果 store 中有进度则直接使用)
const progress = computed(() => playerStore.progress)
</script>

<template>
  <div class="am-mini-player" @click="emit('click')">
    <div class="am-mini-content">
      <div class="am-mini-cover">
        <img 
          :src="song.cover || '/default-cover.png'" 
          :class="{ 'is-playing': isPlaying }"
        />
      </div>
      
      <div class="am-mini-info">
        <div class="am-mini-title">{{ song.title }}</div>
        <div class="am-mini-artist">{{ formatArtist(song.artist) }}</div>
      </div>
      
      <div class="am-mini-controls">
        <button class="am-mini-btn" @click.stop="emit('toggle')" :aria-label="isPlaying ? '暂停' : '播放'">
          <div v-if="isLoading" class="am-mini-loading"></div>
          <svg v-else-if="isPlaying" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16" rx="1"/>
            <rect x="14" y="4" width="4" height="16" rx="1"/>
          </svg>
          <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- 极细进度条 -->
    <div class="am-mini-progress">
      <div class="am-mini-progress-bar" :style="{ width: progress + '%' }"></div>
    </div>
  </div>
</template>

<style scoped>
.am-mini-player {
  position: fixed;
  bottom: 84px; /* 在 TabBar 之上 */
  left: 8px;
  right: 8px;
  height: 64px;
  background: #181818; /* Spotify Card Color */
  border-radius: 8px; /* Spotify Radius */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  z-index: 100;
  border-bottom: 2px solid var(--sp-green); /* Spotify Accent */
}

.am-mini-content {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  height: 100%;
  gap: 12px;
}

.am-mini-cover {
  width: 44px;
  height: 44px;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
  background: #282828;
}

.am-mini-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.am-mini-cover img.is-playing {
  /* Spotify doesn't usually rotate cover, but keeping animation if desired, else remove */
  /* animation: mini-rotate 8s linear infinite; */
}

@keyframes mini-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.am-mini-info {
  flex: 1;
  min-width: 0;
}

.am-mini-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.am-mini-artist {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.am-mini-controls {
  display: flex;
  align-items: center;
}

.am-mini-btn {
  background: none;
  border: none;
  color: var(--text-primary);
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.1s;
}

.am-mini-btn:active {
  transform: scale(0.9);
}

.am-mini-loading {
  width: 20px;
  height: 20px;
  border: 2px solid var(--text-tertiary);
  border-top-color: var(--sp-green);
  border-radius: 50%;
  animation: am-mini-spin 0.8s linear infinite;
}

@keyframes am-mini-spin {
  to { transform: rotate(360deg); }
}

.am-mini-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: rgba(255, 255, 255, 0.1);
}

.am-mini-progress-bar {
  height: 100%;
  background: var(--sp-green);
  transition: width 0.3s linear;
}
</style>
