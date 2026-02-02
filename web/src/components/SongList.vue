<script setup lang="ts">
/**
 * 歌曲列表组件 - Spotify 风格重构版
 * 专注于列表的视觉张力、排版和交互响应。
 */

import { computed, h } from 'vue'
import { NButton, NIcon, NEmpty, NDropdown } from 'naive-ui'
import { 
    PlayCircleOutline, 
    HeartOutline, 
    Heart, 
    EllipsisHorizontal, 
    TrashOutline, 
    FlashOutline, 
    CloudDownloadOutline,
    ChevronUp,
    ChevronDown
} from '@vicons/ionicons5'
import Skeleton from '@/components/common/Skeleton.vue'

const props = defineProps({
  history: { type: Array as () => any[], default: () => [] },
  loading: { type: Boolean, default: false },
  selectedArtistName: { type: String, default: null },
  mode: { type: String, default: 'library' },
  sortField: { type: String, default: 'publish_time' },
  sortOrder: { type: String, default: 'desc' }
})

const emit = defineEmits(['play', 'repair', 'toggleFavorite', 'delete', 'redownload', 'sort'])

const handlePlay = (song: any) => {
  emit('play', song)
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

// Action Menu Options
const renderIcon = (icon: any) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const createRowOptions = (song: any) => [
    {
        label: '重新刮削 (整理信息)',
        key: 'enrich',
        icon: renderIcon(FlashOutline)
    },
    {
        label: '重新下载',
        key: 'redownload',
        icon: renderIcon(CloudDownloadOutline)
    },
    {
        label: '删除歌曲',
        key: 'delete',
        icon: renderIcon(TrashOutline)
    }
]

const handleSelect = (key: string, song: any) => {
    if (key === 'delete') emit('delete', song)
    if (key === 'enrich') emit('repair', song) // Reuse repair/enrich logic
    if (key === 'redownload') emit('redownload', song)
}

const handleSort = (field: string) => {
    emit('sort', field)
}

const getQualityLabel = (quality: any) => {
    if (!quality) return ''
    // If it's already a string label like SQ/HQ/HR
    if (String(quality).match(/^(SQ|HQ|HR|PQ)$/i)) return String(quality).toUpperCase()
    
    // If it's a bitrate number
    const q = parseInt(String(quality))
    if (!isNaN(q)) {
        if (q >= 2000) return 'HR'
        if (q >= 900) return 'SQ' // relaxed threshold for FLAC roughly
        if (q >= 320) return 'HQ'
        return 'PQ'
    }
    // If it's a string like 'PQ', return it
    return String(quality)
}

const getQualityClass = (quality: any) => {
    const label = getQualityLabel(quality)
    if (label === 'HR' || label === 'HI-RES') return 'quality-gold-hires' 
    if (label === 'SQ' || label === 'FLAC') return 'quality-gold-sq'
    if (label === 'HQ') return 'quality-green'
    return 'quality-gray'
}

const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-'
    // Assuming ISO string or similar, take first 10 chars for YYYY-MM-DD
    return String(dateStr).substring(0, 10)
}
</script>

<template>
  <div class="song-list-container">
    <div v-if="loading" class="song-list">
        <!-- 骨架屏表头 -->
        <div class="song-header">
            <div class="index">#</div>
            <div class="title-head">标题</div>
            <div class="artist-head">歌手</div>
            <div class="album-head">专辑</div>
            <div class="date-head">发布时间</div>
            <div class="actions-head"></div>
        </div>
        <!-- 骨架屏行循环 -->
        <div v-for="i in 10" :key="`skel-row-${i}`" class="song-item surface-card">
            <div class="index"><Skeleton width="16px" height="16px" shape="text" /></div>
            <div class="song-info-main">
                <div class="song-cover skeleton-box">
                    <Skeleton width="100%" height="100%" />
                </div>
                <div class="song-meta" style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
                    <Skeleton width="60%" height="16px" />
                </div>
            </div>
            <div class="song-artist"><Skeleton width="60%" height="14px" /></div>
            <div class="song-album"><Skeleton width="80%" height="14px" /></div>
            <div class="song-date"><Skeleton width="50%" height="12px" /></div>
            <div class="song-actions"></div>
        </div>
    </div>
    <div v-else-if="history.length > 0" class="song-list">
      <!-- 表头 -->
      <div class="song-header">
        <div class="index">#</div>
        <div class="title-head sortable" @click="handleSort('title')">
            标题
            <n-icon v-if="sortField === 'title'" :component="sortOrder === 'asc' ? ChevronUp : ChevronDown" class="sort-icon" />
        </div>
        <div class="artist-head">歌手</div>
        <div class="album-head">专辑</div>
        <div class="quality-head">音质</div>
        <div class="date-head sortable" @click="handleSort(mode === 'library' ? 'created_at' : (mode === 'history' ? 'found_at' : 'publish_time'))">
            {{ mode === 'library' ? '添加时间' : (mode === 'history' ? '播放时间' : '发布时间') }}
            <n-icon v-if="(mode === 'library' && sortField === 'created_at') || (mode === 'history' && sortField === 'found_at') || (mode !== 'library' && mode !== 'history' && sortField === 'publish_time')" 
                    :component="sortOrder === 'asc' ? ChevronUp : ChevronDown" 
                    class="sort-icon" />
        </div>
        <div class="actions-head"></div>
      </div>

      <div 
        v-for="(song, index) in history" 
        :key="song.id || index"
        class="song-item surface-card clickable"
        @click="handlePlay(song)"
      >
        <div class="index">{{ index + 1 }}</div>
        
        <div class="song-info-main">
          <img 
            :src="song.cover || '/default-cover.png'" 
            class="song-cover" 
            loading="lazy"
            @error="(e) => (e.target as HTMLImageElement).src = '/default-cover.png'"
          >
          <div class="song-meta">
            <div class="song-title truncate">{{ song.title }}</div>
            <div class="song-sources">
                <template v-if="song.availableSources && song.availableSources.length > 0">
                     <span v-for="src in song.availableSources" :key="src" class="source-tag" :class="src">
                        {{ getSourceName(src) }}
                     </span>
                </template>
                <template v-else>
                     <span class="source-tag" :class="song.source">{{ getSourceName(song.source) }}</span>
                </template>
            </div>
          </div>
        </div>

        <div class="song-artist truncate">{{ song.artist }}</div>
        <div class="song-album truncate">{{ song.album }}</div>
        
        <!-- Quality Badge Column -->
        <div class="song-quality">
            <span v-if="song.quality" 
                  class="quality-badge" 
                  :class="getQualityClass(song.quality)">
                {{ getQualityLabel(song.quality) }}
            </span>
        </div>

        <!-- Date handling is below -->
        

        <div class="song-date">
             <template v-if="mode === 'library'">
                 {{ song.createdAt ? song.createdAt.substring(0, 10) : (song.publishTime ? song.publishTime.substring(0, 10) : '-') }}
             </template>
             <template v-else-if="mode === 'history'">
                 {{ song.foundAt ? song.foundAt.substring(0, 10) : (song.createdAt ? song.createdAt.substring(0, 10) : '-') }}
             </template>
             <template v-else>
                 {{ song.publishTime ? song.publishTime.substring(0, 10) : '-' }}
             </template>
        </div>

        <div class="song-actions">
          <button class="action-btn fav" @click.stop="emit('toggleFavorite', song)">
            <n-icon :component="song.isFavorite ? Heart : HeartOutline" />
          </button>
          
          <n-dropdown 
             trigger="click" 
             :options="createRowOptions(song)" 
             @select="(key) => handleSelect(key, song)"
             @click.stop
          >
             <button class="action-btn" @click.stop>
                <n-icon :component="EllipsisHorizontal" />
             </button>
          </n-dropdown>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <n-empty description="此列表中尚无歌曲" />
    </div>
  </div>
</template>

<style scoped>
.song-list-container {
  width: 100%;
}

/* 调整 Grid 列宽: Index, Title, Artist, Album, Date, Actions */
.song-header, .song-item {
  display: grid;
  /* Columns: Index | Title | Artist | Album | Quality | Date | Actions */
  /* Old: 40px 4fr 2fr 2fr 100px 80px */
  /* New: Added Quality column (60px) */
  /* Index | Title | Artist | Album | Quality | Date | Actions */
  /* 40px | 3fr | 2fr | 2fr | 50px | 90px | 40px */
  grid-template-columns: 32px 3fr 2fr 2fr 50px 90px 40px;
  gap: 4px;
  align-items: center;
}

.song-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.sortable {
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: color 0.2s;
}

.sortable:hover {
    color: #fff;
}

.sort-icon {
    font-size: 14px;
    color: var(--sp-green);
}

.song-item {
  padding: 10px 16px; /* Slightly more compact */
  border-radius: 8px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  margin-bottom: 4px;
}

.song-item:hover {
  background-color: rgba(255, 255, 255, 0.08);
}

.index {
  color: var(--text-secondary);
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-size: 14px;
}

.song-info-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.song-cover {
  width: 42px; /* Slightly smaller cover for tighter list */
  height: 42px;
  border-radius: 6px;
  flex-shrink: 0;
  object-fit: cover;
  background-color: var(--sp-card-hover);
}

.song-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  justify-content: center;
}

.song-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.song-artist {
  font-size: 13px;
  color: var(--text-secondary);
}

.song-sources {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}

.source-tag {
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    background: rgba(255,255,255,0.1);
    color: var(--text-tertiary);
    line-height: 1.4;
}

/* Source Colors for Tags */
.source-tag.qqmusic { color: #20d25c; background: rgba(32, 210, 92, 0.1); }
.source-tag.netease { color: #ec4141; background: rgba(236, 65, 65, 0.1); }
.source-tag.local { color: #409eff; background: rgba(64, 158, 255, 0.1); }
.source-tag.downloaded { color: #409eff; background: rgba(64, 158, 255, 0.1); }

.song-album {
  font-size: 13px;
  color: var(--text-secondary);
}

.quality-head {
  display: flex;
  justify-content: center;
}

.song-quality {
    display: flex;
    justify-content: flex-start;
}

.quality-badge {
    font-size: 10px;
    padding: 1px 4px;
    border-radius: 3px;
    font-weight: 700;
    line-height: 1.2;
    border: 1px solid currentColor;
}

.quality-badge.quality-gold-hires {
    background-color: #000;
    color: #d4af37;
    border: 1px solid #d4af37;
    border-radius: 2px;
    font-weight: 900;
    font-family: serif;
    font-style: italic;
    padding: 0 4px;
    line-height: 12px;
    font-size: 9px;
    letter-spacing: 0.5px;
    box-shadow: none;
}

.quality-badge.quality-gold-sq {
    color: #d4af37;
    border: 1px solid #d4af37;
    background: transparent;
    border-radius: 2px;
    font-weight: 700;
    padding: 0 3px;
}

.quality-badge.quality-green {
    color: #20d25c;
    border: 1px solid #20d25c;
    background: transparent;
    border-radius: 2px;
}

.quality-badge.quality-gray {
    color: #888;
    border: 1px solid #555;
    background: transparent;
    border-radius: 2px;
}

.quality-badge.quality-blue {
    color: #3498db;
    background: rgba(52, 152, 219, 0.1);
    border-color: rgba(52, 152, 219, 0.4);
}

.song-date {
    font-size: 12px;
    color: var(--text-tertiary);
    font-variant-numeric: tabular-nums;
}

.song-item:hover .song-actions {
  opacity: 1;
}

.action-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 18px;
  padding: 4px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}

.action-btn:hover {
  color: #fff;
  transform: scale(1.1);
}

.action-btn.fav {
  color: var(--sp-green);
}

.empty-state {
  padding: 100px 0;
  display: flex;
  justify-content: center;
  color: var(--text-tertiary);
}
</style>
