<script setup lang="ts">
/**
 * 歌曲列表组件 - Spotify 风格重构版
 * 专注于列表的视觉张力、排版和交互响应。
 */

import { computed, h, ref, nextTick } from 'vue'
import { NButton, NIcon, NEmpty, NDropdown, NPopover, NInput, useMessage, NSpin } from 'naive-ui'
import { 
    PlayCircleOutline, 
    HeartOutline, 
    Heart, 
    EllipsisHorizontal, 
    TrashOutline, 
    FlashOutline, 
    CloudDownloadOutline,
    FolderOpenOutline,
    ChevronUp,
    SearchOutline,
    ChevronDown,
    CloudOutline,
    PlaySharp
} from '@vicons/ionicons5'
import Skeleton from '@/components/common/Skeleton.vue'
import { usePlayerStore } from '@/stores/player'

const props = defineProps({
    history: { type: Array as () => any[], default: () => [] },
    loading: { type: Boolean, default: false },
    mode: { type: String as () => 'library' | 'history' | 'discovery' | 'artist', default: 'library' },
    sortField: { type: String, default: 'publish_time' }, // Changed sortBy to sortField for consistency with Home.vue
    sortOrder: { type: String as () => 'asc' | 'desc', default: 'desc' }
})

const emit = defineEmits(['play', 'toggleFavorite', 'repair', 'delete', 'redownload', 'sort'])

const message = useMessage()
const playerStore = usePlayerStore()

// Computed properties for mode-based UI
const showIndex = computed(() => props.mode !== 'discovery')
const showArtist = computed(() => props.mode !== 'artist')
const showPath = computed(() => props.mode === 'library')
const dateLabel = computed(() => {
    if (props.mode === 'history') return '播放时间'
    if (props.mode === 'library') return '添加日期'
    return '发布日期'
})

// Correctly identify which field to use for the date column
const getDateValue = (song: any) => {
    let rawDate = ''
    if (props.mode === 'history') rawDate = song.played_at || '-'
    else if (props.mode === 'library') rawDate = song.created_at || '-'
    else rawDate = song.publish_time || '-'

    if (!rawDate || rawDate === '-') return '-'
    // Format YYYY-MM-DD strictly
    try {
        const dateStr = String(rawDate).split(' ')[0].split('T')[0]
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr
        const date = new Date(rawDate)
        if (!isNaN(date.getTime())) return date.toISOString().split('T')[0]
        return dateStr
    } catch {
        return String(rawDate).substring(0, 10)
    }
}

// Search Logic
const searchQuery = ref('')
const filteredHistory = computed(() => {
    if (!searchQuery.value) return props.history
    const lower = searchQuery.value.toLowerCase()
    return props.history.filter(song => 
        (song.title && song.title.toLowerCase().includes(lower)) ||
        (song.artist && song.artist.name && song.artist.name.toLowerCase().includes(lower)) ||
        (song.album && song.album.toLowerCase().includes(lower))
    )
})

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

// Context Menu Logic
const showDropdown = ref(false)
const x = ref(0)
const y = ref(0)
const currentSong = ref<any>(null)

const handleContextMenu = (e: MouseEvent, song: any) => {
    e.preventDefault()
    showDropdown.value = false
    nextTick().then(() => {
        showDropdown.value = true
        x.value = e.clientX
        y.value = e.clientY
        currentSong.value = song
    })
}

const onClickoutside = () => {
    showDropdown.value = false
}

// Action Menu Options
const renderIcon = (icon: any) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const dropdownOptions = computed(() => {
    if (!currentSong.value) return []
    return [
        {
            label: '播放',
            key: 'play',
            icon: renderIcon(PlayCircleOutline)
        },
        {
            label: '收藏 / 取消收藏',
            key: 'toggleFavorite',
            icon: renderIcon(currentSong.value.liked ? Heart : HeartOutline)
        },
        {
            type: 'divider',
            key: 'd1'
        },
        {
            label: '重新刮削信息',
            key: 'enrich',
            icon: renderIcon(FlashOutline)
        },
        {
            label: '重新下载',
            key: 'redownload',
            icon: renderIcon(CloudDownloadOutline)
        },
        {
            type: 'divider',
            key: 'd2'
        },
        {
            label: '删除',
            key: 'delete',
            icon: renderIcon(TrashOutline)
        }
    ]
})

const handleSelect = (key: string) => {
    showDropdown.value = false
    const song = currentSong.value
    if (!song) return
    
    if (key === 'play') emit('play', song)
    if (key === 'toggleFavorite') emit('toggleFavorite', song)
    if (key === 'delete') emit('delete', song)
    if (key === 'enrich') emit('repair', song)
    if (key === 'redownload') emit('redownload', song)
}

// 排序处理
const handleSort = (field: string) => {
    let newOrder: 'asc' | 'desc' = 'desc'
    if (props.sortField === field) {
        newOrder = props.sortOrder === 'asc' ? 'desc' : 'asc'
    } else {
        // 默认按降序排
        newOrder = 'desc'
    }
    emit('sort', { field, order: newOrder })
}

const getSortIcon = (field: string) => {
    if (props.sortField !== field) return undefined
    return props.sortOrder === 'desc' ? ChevronDown : ChevronUp
}

const getQualityLabel = (quality: any) => {
    if (!quality) return ''
    if (String(quality).match(/^(SQ|HQ|HR|PQ)$/i)) return String(quality).toUpperCase()
    
    const q = parseInt(String(quality))
    if (!isNaN(q)) {
        if (q >= 2000) return 'HR'
        if (q >= 900) return 'SQ'
        if (q >= 320) return 'HQ'
        return 'PQ'
    }
    return String(quality)
}

const getQualityClass = (quality: any) => {
    const label = getQualityLabel(quality)
    if (label === 'HR' || label === 'HI-RES') return 'quality-gold-hires' 
    if (label === 'SQ' || label === 'FLAC') return 'quality-sq-green' // Classic Green for Lossless
    if (label === 'HQ') return 'quality-hq-blue' // Geek Blue for High Quality
    if (label === 'ERR') return 'quality-error'
    return 'quality-gray' // PQ / Standard
}

const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-'
    return String(dateStr).substring(0, 10)
}

const formatShortPath = (path: string | null | undefined) => {
    if (!path) return ''
    
    // Normalize slashes to forward slash for display
    const normalizedPath = path.replace(/\\/g, '/')
    
    // Do NOT remove extension
    
    const keywords = ['favorites', 'audio_cache', 'library', 'media', 'music', 'shares', 'download']
    const lowerPath = normalizedPath.toLowerCase()
    
    for (const kw of keywords) {
        const index = lowerPath.lastIndexOf(kw)
        if (index !== -1) {
            // Return from the keyword to the end
            return normalizedPath.substring(index)
        }
    }
    
    // Fallback: take the last directory + filename
    const parts = normalizedPath.split('/').filter(p => p)
    if (parts.length >= 2) {
        return parts.slice(-2).join('/')
    }
    return normalizedPath.split('/').pop() || normalizedPath
}

const formatArtist = (artist: any) => {
  if (!artist) return '未知歌手'
  if (typeof artist === 'string') return artist
  if (Array.isArray(artist)) return artist.map(a => a.name).join(', ')
  if (artist.name) return artist.name
  return '未知歌手'
}

const formatPath = (path: string | null | undefined) => {
  // Alias to formatShortPath for backward compatibility if needed, 
  // or just use formatShortPath in template.
  return formatShortPath(path)
}

const getPlatformLabel = (source: string) => {
    switch (source.toLowerCase()) {
        case 'netease': return '网易'
        case 'qqmusic': return 'QQ'
        case 'local': return '本地'
        default: return source
    }
}
</script>

<template>
  <div class="song-list-container">
    
    <!-- Tools / Filter Bar -->
    <div class="list-tools">
        <div class="search-box">
             <n-input 
                v-model:value="searchQuery" 
                placeholder="在资料库中筛选..." 
                clearable
                round
                size="small"
            >
                <template #prefix>
                    <n-icon :component="SearchOutline" />
                </template>
            </n-input>
        </div>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="song-list loading">
        <div class="song-header">
            <div class="col-index">#</div>
            <div class="col-title">标题</div>
            <!-- 歌手列：支持排序 -->
            <div class="col col-artist sortable" @click="handleSort('artist')">
                歌手
                <n-icon v-if="sortField === 'artist'" :component="getSortIcon('artist')" class="sort-icon" />
            </div>
            <!-- 专辑列 -->
            <div class="col col-album">专辑</div>
            <!-- 时间列：支持排序 -->
            <div class="col col-time sortable" @click="handleSort('created_at')">
                添加时间
                <n-icon v-if="sortField === 'created_at'" :component="getSortIcon('created_at')" class="sort-icon" />
            </div>
            <div class="col-duration"><n-icon :component="FolderOpenOutline" /></div>
        </div>
        <div v-for="i in 10" :key="`skel-${i}`" class="song-row">
            <Skeleton width="100%" height="40px" />
        </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredHistory.length === 0" class="empty-state">
        <n-empty description="没有找到歌曲" size="large">
            <template #icon>
                <n-icon :component="FolderOpenOutline" />
            </template>
        </n-empty>
    </div>

    <!-- Actual List -->
    <div v-else class="song-list">
        <!-- Table Header -->
        <div class="song-list-header">
          <div v-if="showIndex" class="col-index">#</div>
          <div class="col-title" :style="{ marginLeft: !showIndex ? '16px' : '0' }">标题</div>
          <div v-if="showArtist" class="col-artist">艺人</div>
          <div class="col-album">专辑</div>
          <div class="col-date sortable" @click="handleSort('publish_time')">
            {{ dateLabel }}
            <n-icon v-if="sortField === 'publish_time' || sortField === 'created_at'" 
                    :component="sortOrder === 'desc' ? ChevronDown : ChevronUp" 
                    class="sort-icon" />
          </div>
          <div v-if="showPath" class="col-path">文件位置</div>
          <div class="col-more"></div>
        </div>

        <!-- Table Row -->
        <div 
          v-for="(song, index) in filteredHistory" 
          :key="song.id || index" 
          class="song-row"
          :class="{ 'is-active': playerStore.currentSong?.id === song.id }"
          @click="handlePlay(song)"
          @contextmenu="handleContextMenu($event, song)"
        >
          <!-- Index / Play Icon -->
          <div v-if="showIndex" class="col-index">
            <span class="index-num">{{ index + 1 }}</span>
            <n-icon :component="PlaySharp" class="play-icon" />
          </div>

          <!-- Title & Cover -->
          <div class="col-title" :style="{ paddingLeft: !showIndex ? '16px' : '0' }">
            <div class="title-with-cover">
              <div class="cover-container" :class="{ 'discovery-cover': mode === 'discovery' }">
                <img :src="song.cover || '/default-cover.png'" class="song-cover" loading="lazy">
                <div v-if="song.status === 'PENDING'" class="loading-overlay">
                    <n-spin size="small" stroke="var(--sp-green)" />
                </div>
              </div>
              <div class="title-info">
                <div class="song-name truncate" :class="{ 'text-green': playerStore.currentSong?.id === song.id }">
                  {{ song.title }}
                </div>
                <!-- Platform Info -->
                <div class="title-meta">
                   <div v-if="song.available_sources && song.available_sources.length > 0" class="source-tags">
                        <span v-for="s in song.available_sources" :key="s" 
                              class="platform-tag" 
                              :class="s">
                            {{ getPlatformLabel(s) }}
                        </span>
                   </div>
                   <div v-else-if="song.source" class="source-tags">
                        <span class="platform-tag" :class="song.source">
                            {{ getPlatformLabel(song.source) }}
                        </span>
                   </div>
                   <!-- Quality Badge (Only in Library) -->
                   <div class="quality-badges" v-if="song.quality && mode === 'library'">
                        <span class="quality-tag" :class="getQualityClass(song.quality)">
                            {{ getQualityLabel(song.quality) }}
                        </span>
                   </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Artist -->
          <div v-if="showArtist" class="col-artist truncate hover-white">
            {{ formatArtist(song.artist) }}
          </div>

          <!-- Album -->
          <div class="col-album truncate hover-white">
            {{ song.album || '-' }}
          </div>

          <!-- Release Date -->
          <div class="col-date truncate">
            {{ getDateValue(song) }}
          </div>

          <!-- File Path (Compact) -->
          <div v-if="showPath" class="col-path">
            <div class="path-pill truncate" :title="song.local_path">
                <n-icon :component="FolderOpenOutline" class="path-icon" />
                <span class="path-text">{{ formatShortPath(song.local_path) }}</span>
            </div>
          </div>

          <!-- Like Button -->
          <div class="col-like" @click.stop="emit('toggleFavorite', song)">
              <n-icon size="18" :class="['like-icon', { 'liked': song.is_favorite }]">
                  <Heart v-if="song.is_favorite" />
                  <HeartOutline v-else />
              </n-icon>
          </div>
        </div>
    </div>

    <!-- Context Menu -->
    <n-dropdown
        placement="bottom-start"
        trigger="manual"
        :x="x"
        :y="y"
        :options="dropdownOptions"
        :show="showDropdown"
        :on-clickoutside="onClickoutside"
        @select="handleSelect"
    />

  </div>
</template>

<style scoped>
.song-list-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    color: #b3b3b3;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    user-select: none;
}

.list-tools {
    padding: 0 16px 16px 16px;
    display: flex;
    justify-content: flex-start;
}

.search-box {
    width: 240px;
}

/* Table Header */
.song-list-header {
    display: flex;
    align-items: center;
    padding: 0 16px;
    height: 32px;
    color: #4d4d4d; /* More subtle header */
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 8px;
}

.song-list-header > div {
    display: flex;
    justify-content: center; 
    align-items: center;
}
/* 表头微调：左对齐并设置左边距以匹配红字标注位置 */
.song-list-header > .col-title, 
.song-list-header > .col-artist, 
.song-list-header > .col-album {
    justify-content: flex-start !important;
    padding-left: 10px; /* 向左偏移的视觉补偿 */
}
/* 文件路径表头：按要求左对齐 */
.song-list-header > .col-path {
    justify-content: flex-start !important;
    padding-left: 20px;
}

/* 标题列在表头保持居中对齐 */
.song-list-header > .col-title {
    justify-content: center;
    padding-left: 0;
}

.sticky-header {
    position: sticky;
    top: 0;
    background: #121212; /* Keep strictly dark */
    z-index: 10;
}

.sortable {
    cursor: pointer;
    transition: color 0.2s;
    display: flex;
    align-items: center;
    gap: 4px;
}
.sortable:hover {
    color: #fff;
}
.sort-icon {
    font-size: 14px;
}

/* Columns Grid - Standard Mode (Standard Standard widths when Path is hidden) */
.col-index { width: 40px; text-align: center; justify-content: center; display: flex; align-items: center; color: #5e5e5e; font-size: 13px;}
.col-title { flex: 1; min-width: 200px; display: flex; align-items: center; overflow: hidden; margin-right: 12px; }
.col-artist { flex: 0 0 20%; min-width: 120px; overflow: hidden; display: flex; align-items: center; margin-right: 12px; }
.col-album { flex: 0 0 20%; min-width: 120px; overflow: hidden; display: flex !important; align-items: center; margin-right: 12px; }
.col-date { width: 120px; display: flex; justify-content: flex-end; align-items: center; color: #b3b3b3; font-size: 13px; padding-right: 16px; white-space: nowrap;}
.col-path { flex: 0 0 25%; display: flex; align-items: center; overflow: hidden; padding-left: 20px; } 

/* 资料库模式下的列宽重写 (When File Path is visible, compress others) */
.song-list-container:has(.col-path) .col-title { flex: 0 0 25%; }
.song-list-container:has(.col-path) .col-artist { flex: 0 0 15%; }
.song-list-container:has(.col-path) .col-album { flex: 0 0 15%; }
.song-list-container:has(.col-path) .col-date { width: 100px; padding-right: 8px;}
.col-like { width: 40px; display: flex; justify-content: center; align-items: center; }
.col-more { width: 40px; } /* For dropdown ellipsis */

.path-content {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    overflow: hidden;
}

.path-text {
    font-size: 0.75rem;
    color: #a0a0a0; /* Lighter gray for better visibility on dark background */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.like-icon {
    cursor: pointer;
    color: #888;
    transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.like-icon:hover {
    color: #fff;
    transform: scale(1.2);
}

.like-icon.liked {
    color: #ff4d4f;
}
/* Title Column Styles */
.title-with-cover {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
}

.cover-container {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    position: relative;
    border-radius: 4px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    transition: transform 0.3s cubic-bezier(0.19, 1, 0.22, 1);
}

.song-cover {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.title-info {
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
    gap: 2px;
}

.song-name {
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.2;
}

.title-meta {
    display: flex;
    align-items: center;
    gap: 4px;
}

.source-tags {
    display: flex;
    gap: 4px;
}

.platform-tag {
    font-size: 9px;
    padding: 0px 6px;
    border-radius: 12px; /* Capsule shape */
    font-weight: 600;
    letter-spacing: 0.03em;
    line-height: 1.6;
    background: transparent; /* Subtle background */
    border: 0.5px solid rgba(255,255,255,0.12); /* Ultra-thin border */
    color: #777;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* More refined colors for tags - Very low saturation */
.platform-tag.netease { color: rgba(242, 93, 142, 0.7); border-color: rgba(242, 93, 142, 0.15); }
.platform-tag.qqmusic { color: rgba(255, 204, 51, 0.7); border-color: rgba(255, 204, 51, 0.15); }
.platform-tag.local { color: rgba(29, 185, 84, 0.7); border-color: rgba(29, 185, 84, 0.15); }

.platform-tag:hover {
    background: rgba(255,255,255,0.08);
    color: #fff;
}

.song-name {
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin-bottom: 1px;
}

.quality-tag {
    font-size: 9px;
    padding: 0px 4px;
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 2px;
    color: var(--text-secondary);
    font-weight: 700;
    letter-spacing: 0.05em;
}

.quality-tag.error {
    color: #ff4d4f;
    border-color: #ff4d4f;
}

.discovery-cover {
    width: 48px !important;
    height: 48px !important;
}

.song-row:hover .cover-container {
    transform: scale(1.05);
}

.song-row:hover .song-name {
    color: #fff;
}

.text-green {
    color: var(--sp-green) !important;
}

.loading-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
}

.hover-white:hover {
    color: #fff;
}

/* Rows */
.song-row {
    display: flex;
    align-items: center;
    padding: 12px 16px; /* Increased padding for more breathing room */
    min-height: 64px; /* Increased min-height */
    border-radius: 4px;
    transition: background-color 0.2s;
    cursor: pointer;
}

.song-row:hover {
    background-color: rgba(255, 255, 255, 0.1);
}

.song-row.active {
    background-color: rgba(255, 255, 255, 0.2);
}

.song-row:hover .index-num { display: none; }
.song-row:hover .play-icon { display: flex; color: #fff; }
.play-icon { display: none; font-size: 18px; }

/* Title Column Styles */
.title-wrap {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    justify-content: flex-start;
}
.row-cover {
    width: 40px;
    height: 40px;
    object-fit: cover;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
}
.title-text {
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
}
.song-name {
    color: #fff;
    font-size: 1rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.2;
}
.playing { color: #1db954; }

.quality-badges {
    display: flex;
    gap: 4px;
}

.quality-tag {
    font-size: 10px;
    padding: 0px 4px;
    border-radius: 2px;
    border: 1px solid currentColor;
    line-height: 1.3;
    font-weight: 700;
    text-transform: uppercase;
    transition: all 0.3s ease;
}

/* 移除突兀的红色，PQ 标签使用更中性的灰色/暗色 */
.quality-red { 
    color: #666; 
    border-color: #333; 
    background: rgba(255,255,255,0.03);
}





/* CSS Updates in style tag */
/* 
   New Palette:
   HR: #FFD700 (Gold)
   SQ: #1DB954 (Spotify Green)
   HQ: #2E86DE (Geek Blue)
   PQ: #888888 (Gray)
*/

.quality-gold-hires {
    color: #FFD700;
    border-color: rgba(255, 215, 0, 0.5);
    background: rgba(255, 215, 0, 0.1);
    box-shadow: 0 0 8px rgba(255, 215, 0, 0.2);
    text-shadow: 0 0 4px rgba(255, 215, 0, 0.4);
}

.quality-sq-green {
    color: #1DB954;
    border-color: rgba(29, 185, 84, 0.5);
    background: rgba(29, 185, 84, 0.1);
}

.quality-hq-blue {
    color: #4facfe; /* Lighter blue for dark theme */
    border-color: rgba(79, 172, 254, 0.5);
    background: rgba(79, 172, 254, 0.1);
}

.quality-gray { 
    color: #888; 
    border-color: #555; 
    background: rgba(255,255,255,0.05);
} 


.quality-error {
    color: #ff4d4f;
    border-color: #ff4d4f;
    background: rgba(255, 77, 79, 0.1);
}

.path-icon {
    opacity: 0.5;
    transition: all 0.2s ease;
}

.song-row:hover .path-icon {
    opacity: 1;
}

.path-icon.local {
    color: #1db954; /* 经典的 Spotify 绿 */
}

.path-icon.cloud {
    color: #666;
}

/* Quality Colors */
.quality-gold-hires { color: #FFD700; border-color: #FFD700; }
.quality-gold-sq { color: #FFA500; border-color: #FFA500; }
.quality-green { color: #1db954; border-color: #1db954; }
.quality-gray { color: #666; border-color: #666; }

/* Source Dots */
.source-badges { display: inline-flex; gap: 2px; }
.source-dot {
    width: 6px; 
    height: 6px; 
    border-radius: 50%; 
    background-color: #555;
    opacity: 0.7;
}
.source-dot.netease { background-color: #c20c0c; }
.source-dot.qqmusic { background-color: #2cad6f; }
.source-dot.local { background-color: #f1c40f; }

/* Text Styles */
.artist-name, .album-name {
    color: var(--text-secondary);
    font-size: 14px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
    transition: color 0.2s;
}
.song-row:hover .artist-name, .song-row:hover .album-name {
    color: #fff;
}
.col-date { color: #b3b3b3; font-size: 0.85rem; }

/* Path column */
.path-col .path-content {
    font-size: 0.75rem;
    padding: 2px 4px; /* 缩窄留白，从 8px 降至 4px */
    background: rgba(255,255,255,0.05); 
    border-radius: 12px;
    color: #888;
    transition: all 0.2s ease;
    max-width: 100%;
}
.song-row:hover .path-content {
    background: rgba(255,255,255,0.1);
    color: #fff;
}
.path-col .path-text { color: inherit; }
.path-col .path-text.text-gray { background: transparent; }

/* Empty State */
.empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding-top: 40px;
}
</style>
