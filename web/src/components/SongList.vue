<script setup>
import { NButton, NIcon, NEmpty } from 'naive-ui'
import { CloseOutline, PlayCircleOutline } from '@vicons/ionicons5'

const props = defineProps({
  history: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  selectedArtistName: { type: String, default: null },
  oneWord: { type: String, default: '' }
})

const emit = defineEmits(['play', 'clear-filter'])

const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now - date
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) return '今天'
    if (days === 1) return '昨天'
    if (days < 30) return `${days}天前`
    
    const year = date.getFullYear()
    const month = date.getMonth() + 1
    const day = date.getDate()
    return `${year === now.getFullYear() ? '' : year + '/'}${month}/${day}`
}

const handlePlay = (song) => {
    emit('play', song)
}

const handleClearHelper = () => {
    emit('clear-filter')
}
</script>

<template>
    <section class="feed-section">
        <h2 class="section-title">
            {{ selectedArtistName ? `🎵 ${selectedArtistName}` : '📢 最新动态' }}
            <span v-if="!selectedArtistName && oneWord" class="one-word-badge">{{ oneWord }}</span>
            <n-button v-if="selectedArtistName" text size="tiny" class="clear-filter-btn" @click="handleClearHelper">
                <template #icon><n-icon><CloseOutline /></n-icon></template>
                ❎ 清除筛选
            </n-button>
        </h2>
        
        <div v-if="loading" class="skeleton-table">
             <div v-for="i in 5" :key="i" class="table-row skeleton-row">
                 <div class="col-cover skeleton"></div>
                 <div class="col-track skeleton" style="width: 40%; height: 20px;"></div>
                 <div class="col-artist skeleton" style="width: 20%; height: 20px; margin-left: auto;"></div>
             </div>
        </div>

        <div class="song-table" v-else-if="history.length > 0">
                <div class="table-header">
                    <div class="col-cover"></div>
                    <div class="col-track">🎵 歌曲</div>
                    <div class="col-artist">👤 歌手</div>
                    <div class="col-album">💿 专辑</div>
                    <div class="col-time">📅 发布时间</div>
                    <div class="col-action"></div>
                </div>
                
                <div v-for="(song, index) in history" :key="song.unique_key" 
                     class="table-row stagger-anim"
                     :style="{ animationDelay: `${index * 0.05}s` }">
                    <!-- Cover -->
                    <div class="col-cover">
                        <div class="cover-wrapper">
                            <img :src="song.cover || `https://ui-avatars.com/api/?name=${song.title}&length=1&background=random&size=128`" 
                                 class="song-cover-img" 
                                 loading="lazy" />
                            <div class="play-overlay" @click.stop="handlePlay(song)">
                                <n-icon><PlayCircleOutline /></n-icon>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Track Info -->
                    <div class="col-track">
                         <div class="track-name" :title="song.title">{{ song.title }}
                             <span v-if="song.source === 'netease'" class="platform-dot netease" title="网易云"></span>
                             <span v-if="song.source === 'qqmusic'" class="platform-dot qq" title="QQ音乐"></span>
                         </div>
                    </div>
                    
                    <!-- Artist -->
                    <div class="col-artist">
                        {{ song.author }}
                    </div>
                    
                    <!-- Album -->
                    <div class="col-album" :title="song.album">
                        {{ song.album || '-' }}
                    </div>
                    
                    <!-- Time -->
                    <div class="col-time" :title="song.publish_time">
                        {{ formatDate(song.publish_time) }}
                    </div>
                    
                    <!-- Action -->
                    <div class="col-action">
                         <a href="javascript:void(0)" @click.stop="handlePlay(song)" class="action-link">
                             播放
                         </a>
                    </div>
                </div>
            </div>
            
            <div v-else class="empty-state">
                <n-empty description="📭 暂无最新动态，岁月静好" size="large" />
            </div>
    </section>
</template>

<style scoped>
.section-title {
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.one-word-badge {
    display: inline-block;
    font-size: 13px;
    font-weight: 400;
    color: #86868B;
    background: transparent;
    margin-left: 12px;
    font-style: italic;
    font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
    vertical-align: middle;
    opacity: 0.8;
}

/* Feed Song Table (iTunes Style) */
.song-table {
    display: flex;
    flex-direction: column;
}
.table-header {
    display: flex;
    padding: 0 16px 12px;
    border-bottom: 1px solid #E5E5E5;
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 500;
}
.table-row {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    border-radius: 8px;
    margin-bottom: 2px;
    transition: background 0.1s;
}
.table-row:hover {
    background: rgba(255, 255, 255, 0.95);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    transform: scale(1.01);
    transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);
}

/* Columns */
.col-cover { width: 56px; margin-right: 16px; }
.col-track { flex: 2; min-width: 0; font-weight: 500; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
.col-artist { flex: 1; min-width: 0; color: var(--text-primary); }
.col-album { flex: 1.5; min-width: 0; color: var(--text-secondary); }
.col-time { width: 100px; text-align: right; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.col-action { width: 60px; text-align: right; opacity: 0; transition: opacity 0.2s; }
.table-row:hover .col-action { opacity: 1; }

.cover-wrapper {
    width: 48px; /* Slightly larger */
    height: 48px;
    position: relative;
    border-radius: 8px; /* Softer radius */
    overflow: hidden;
    background: #f2f2f7;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    transition: transform 0.2s;
}
.song-cover-img { width: 100%; height: 100%; object-fit: cover; }
.play-overlay {
    position: absolute;
    top:0; left:0; right:0; bottom:0;
    background: rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 20px;
    opacity: 0;
    cursor: pointer;
}
.cover-wrapper:hover .play-overlay { opacity: 1; }

.track-name { 
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; 
}
.platform-dot {
    width: 6px; height: 6px; border-radius: 50%; display: inline-block; flex-shrink: 0;
}
.platform-dot.netease { background-color: var(--accent-netease); }
.platform-dot.qq { background-color: var(--accent-qq); }

.col-artist, .col-album {
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px;
}
.col-time { font-size: 13px; }

.action-link {
    font-size: 13px;
    color: var(--accent-primary);
    font-weight: 500;
}

/* Skeleton Specific */
.skeleton-table { padding: 0 16px; }
.skeleton-row {
    height: 64px;
    align-items: center;
    gap: 16px;
}
.skeleton-row .col-cover.skeleton {
    width: 44px; height: 44px; border-radius: 6px;
}
.skeleton { background: rgba(0,0,0,0.06); border-radius: 4px; animation: pulse 1.5s infinite; }
@keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }

.table-row:hover .cover-wrapper {
     transform: scale(1.05) translateZ(0); /* Subtle pop for album art */
}

.empty-state { text-align: center; padding: 40px; }

/* 深色模式 */
:root[data-theme="dark"] .section-title {
    color: var(--text-primary);
}
:root[data-theme="dark"] .one-word-badge {
    color: var(--text-secondary);
}
:root[data-theme="dark"] .table-header {
    border-color: rgba(255, 255, 255, 0.1);
}
:root[data-theme="dark"] .table-row:hover {
    background: rgba(255, 255, 255, 0.06);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
:root[data-theme="dark"] .cover-wrapper {
    background: #2C2C2E;
}
:root[data-theme="dark"] .skeleton {
    background: rgba(255, 255, 255, 0.08);
}
</style>
