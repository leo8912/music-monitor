<template>
  <div 
    class="song-card" 
    :class="{ compact, clickable }"
    @click="handleClick"
  >
    <!-- 封面 -->
    <img 
      v-if="showCover && song.cover" 
      :src="song.cover" 
      class="song-cover"
      :class="{ compact }"
      loading="lazy"
      @error="(e) => (e.target as HTMLImageElement).src = '/default-cover.png'"
    />
    
    <!-- 信息 -->
    <div class="song-info">
      <div class="song-title">{{ song.title }}</div>
      <div v-if="showArtist" class="song-artist">{{ song.artist }}</div>
      <div v-if="showAlbum" class="song-album">{{ song.album }}</div>
    </div>
    
    <!-- 来源指示器 -->
    <div v-if="showSource && song.available_sources" class="song-sources">
      <span 
        v-for="src in song.available_sources" 
        :key="src" 
        class="source-tag" 
        :class="src"
      >
        {{ getSourceName(src) }}
      </span>
    </div>
    
    <!-- 操作按钮 -->
    <div v-if="showActions" class="song-actions">
      <button @click.stop="$emit('play', song)" class="btn-action">
        <n-icon :component="PlayCircleOutline" />
      </button>
      <button 
        @click.stop="$emit('favorite', song)" 
        class="btn-action btn-favorite"
        :class="{ active: song.is_favorite }"
      >
        <n-icon :component="song.is_favorite ? Heart : HeartOutline" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 通用歌曲卡片组件
 * 
 * 用于统一歌曲展示样式,减少重复代码
 * 
 * Author: google
 * Created: 2026-01-30
 */
import { NIcon } from 'naive-ui'
import { PlayCircleOutline, HeartOutline, Heart } from '@vicons/ionicons5'
import type { Song } from '@/types'

interface Props {
  song: Song
  showCover?: boolean
  showArtist?: boolean
  showAlbum?: boolean
  showSource?: boolean
  showActions?: boolean
  compact?: boolean
  clickable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showCover: true,
  showArtist: true,
  showAlbum: false,
  showSource: true,
  showActions: true,
  compact: false,
  clickable: true
})

const emit = defineEmits<{
  click: [song: Song]
  play: [song: Song]
  favorite: [song: Song]
}>()

const handleClick = () => {
  if (props.clickable) {
    emit('click', props.song)
  }
}

const getSourceName = (source: string) => {
  const map: Record<string, string> = {
    'netease': '网易云',
    'qqmusic': 'QQ音乐',
    'local': '本地',
    'manual': '手动'
  }
  return map[source] || source
}
</script>

<style scoped>
.song-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  transition: background 0.2s;
}

.song-card.clickable {
  cursor: pointer;
}

.song-card.clickable:hover {
  background: rgba(255, 255, 255, 0.08);
}

.song-card.compact {
  padding: 8px;
  gap: 8px;
}

.song-cover {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  object-fit: cover;
  flex-shrink: 0;
}

.song-cover.compact {
  width: 32px;
  height: 32px;
}

.song-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.song-title {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.song-artist,
.song-album {
  font-size: 12px;
  color: #b3b3b3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.song-sources {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.source-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  color: #b3b3b3;
}

.source-tag.qqmusic {
  color: #20d25c;
  background: rgba(32, 210, 92, 0.1);
}

.source-tag.netease {
  color: #ec4141;
  background: rgba(236, 65, 65, 0.1);
}

.source-tag.local {
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.song-actions {
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.song-card:hover .song-actions {
  opacity: 1;
}

.btn-action {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: #b3b3b3;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.btn-action:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.btn-favorite.active {
  color: #1DB954;
}
</style>
