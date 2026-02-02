<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { NModal, NCard, NInput, NButton, NIcon, NSpin, NEmpty, useMessage, NRadioGroup, NRadioButton } from 'naive-ui'
import { SearchOutline, CheckmarkCircle, RefreshOutline, ArrowBackOutline, CloudDownloadOutline, HourglassOutline } from '@vicons/ionicons5'
import { searchSongs, searchDownload, probeQualities } from '@/api/discovery'
import { matchMetadata, redownloadSong } from '@/api/library'
import { usePlayerStore } from '@/stores/player'
import { useLibraryStore } from '@/stores/library'

const props = defineProps({
  show: Boolean,
  song: { type: Object, default: null },
  mode: { type: String, default: 'metadata' } // 'metadata' | 'download'
})

const emit = defineEmits(['update:show', 'success'])

const keyword = ref('')
const loading = ref(false)
const results = ref<any[]>([])
const stats = ref({ netease: 0, qqmusic: 0, total: 0 })
const message = useMessage()
const processing = ref(false)
const hasSearched = ref(false)
const playerStore = usePlayerStore()
const libraryStore = useLibraryStore()
const currentStep = ref(1) // 1: Search List, 2: Quality Selection
const selectedResult = ref<any>(null)
const selectedQuality = ref(999)
const probedQualities = ref<any[]>([])
const probing = ref(false)

// Init keyword when song changes
watch(() => props.song, (newSong) => {
    if (newSong) {
        keyword.value = newSong.title
        results.value = []
        stats.value = { netease: 0, qqmusic: 0, total: 0 }
        hasSearched.value = false
        currentStep.value = 1
        selectedResult.value = null
    }
}, { immediate: true })

const handleClose = () => {
    emit('update:show', false)
}

const handleSearch = async () => {
    if (!keyword.value) return
    loading.value = true
    hasSearched.value = true
    currentStep.value = 1 // Reset to list
    try {
        let res: any[] = []
        if (props.mode === 'download') {
            res = await searchDownload({
                keyword: keyword.value,
                limit: 5
            })
        } else {
            res = await searchSongs({
                keyword: keyword.value,
                limit: 20
            })
        }
        
        // 1. Calculate Stats
        stats.value = {
            netease: res.filter(i => i.source === 'netease').length,
            qqmusic: res.filter(i => i.source === 'qqmusic').length,
            total: res.length
        }

        // 2. Results display
        if (props.mode === 'download') {
            // For download mode (GDStudio), show top rankings directly as sorted by backend
            results.value = res.slice(0, 20)
        } else {
            // For metadata mode (Netease/QQ), interleave as before
            const netease = res.filter(i => i.source === 'netease')
            const qqmusic = res.filter(i => i.source === 'qqmusic')
            const combined = []
            const maxLen = Math.max(netease.length, qqmusic.length)
            for (let i = 0; i < maxLen; i++) {
                if (i < qqmusic.length) combined.push(qqmusic[i])
                if (i < netease.length) combined.push(netease[i])
            }
            results.value = combined
        }
    } catch (e) {
        message.error('搜索失败')
    } finally {
        loading.value = false
    }
}

const handleMatch = async (target: any) => {
    if (props.mode === 'download' && currentStep.value === 1) {
        // Step 1 -> 2: Select item and move to quality selection
        selectedResult.value = target
        currentStep.value = 2
        
        // Dynamic Probing
        probing.value = true
        probedQualities.value = []
        try {
            const res = await probeQualities({
                source: target.source,
                id: target.id
            })
            probedQualities.value = res
            // Pick highest available as default
            if (res.length > 0) {
                selectedQuality.value = res[0].quality
            }
        } catch (e) {
            message.error('质量探测失败')
        } finally {
            probing.value = false
        }
        return
    }

    if (processing.value) return
    processing.value = true
    try {
        if (props.mode === 'download') {
            const res = await redownloadSong({
                song_id: props.song.id,
                source: selectedResult.value.source,
                track_id: selectedResult.value.id,
                quality: selectedQuality.value,
                title: selectedResult.value.title,
                artist: selectedResult.value.artist
            })
            
            if (res.success && res.song) {
                // 1. 更新资料库列表中的数据
                const updatedSong = libraryStore.updateSongInList(res.song)
                
                // 2. 如果当前正在播放这首歌，自动重载
                if (playerStore.currentSong && playerStore.currentSong.id === props.song.id && updatedSong) {
                    const oldTime = playerStore.currentTime
                    const wasPlaying = playerStore.isPlaying
                    
                    message.success('下载成功，正在为您无缝升级音质...')
                    
                    // 重新播放新路径
                    await playerStore.playSong(updatedSong)
                    
                    // 尝试恢复进度
                    if (wasPlaying) {
                        setTimeout(() => {
                            playerStore.seekTo((oldTime / playerStore.duration) * 100)
                        }, 500)
                    }
                } else {
                    message.success('已开始重新下载')
                }
            } else {
                 message.success('已开始重新下载')
            }
        } else {
            const payload = {
                song_id: props.song.id,
                target_source: target.source,
                target_song_id: target.id
            }
            await matchMetadata(payload)
            message.success('匹配成功')
        }
        
        emit('success')
        handleClose()
    } catch (e) {
        message.error((props.mode === 'download' ? '下载失败: ' : '匹配失败: ') + (e as Error).message)
    } finally {
        processing.value = false
    }
}

const getSourceParams = (s: string) => {
    if (s === 'qqmusic') return { label: 'QQ', color: '#1db954' } // Spotify green for QQ? Or keep distinct? QQ is usually Green/Yellow. Let's use Spotify Green for UI consistnecy
    if (s === 'netease') return { label: '网易', color: '#C20C0C' }
    return { label: s, color: '#888' }
}

const formatQuality = (br: number) => {
    if (!br) return ''
    if (br >= 999) return 'FLAC'
    if (br >= 740) return 'SQ'
    if (br >= 320) return '320K'
    if (br >= 192) return '192K'
    return br + 'K'
}

const formatSize = (bytes: number) => {
    if (!bytes) return ''
    if (bytes > 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
    return (bytes / 1024).toFixed(1) + 'KB'
}
</script>

<template>
  <n-modal :show="show" @update:show="(v) => emit('update:show', v)">
    <div class="spotify-modal">
        <!-- Header -->
        <div class="modal-header">
            <h3>{{ props.mode === 'download' ? '重新下载' : '修复元数据' }}</h3>
            <div class="search-container">
                <div class="search-input-wrapper">
                    <n-icon :component="SearchOutline" class="search-icon" />
                    <input 
                        v-model="keyword" 
                        placeholder="想听什么？" 
                        class="spotify-input"
                        @keydown.enter="handleSearch"
                    />
                </div>
                <!-- Search Button Back -->
                <n-button 
                    type="primary" 
                    color="#1db954" 
                    class="search-btn"
                    @click="handleSearch" 
                    :loading="loading"
                    round
                >
                    搜索
                </n-button>
            </div>
        </div>

        <!-- Content -->
        <div class="modal-content">
            <!-- Step 1: Search Result List -->
            <div v-if="currentStep === 1">
                <!-- Stats Bar -->
                <div class="stats-bar" v-if="loading || stats.total > 0">
                    <span v-if="loading">搜索中...</span>
                    <span v-else>
                        找到 {{ stats.total }} 个结果 
                        <span class="source-stat" v-if="props.mode !== 'download'">(QQ: {{ stats.qqmusic || 0 }} · 网易: {{ stats.netease || 0 }})</span>
                    </span>
                </div>

                <n-spin :show="loading || processing" style="min-height: 200px">
                    <div v-if="results.length > 0" class="track-list">
                        <div 
                            v-for="item in results" 
                            :key="item.id + item.source" 
                            class="track-row" 
                            @click="handleMatch(item)"
                        >
                            <div class="track-img-col">
                                <img :src="item.cover_url || item.cover || '/default-cover.png'" class="track-cover" referrerpolicy="no-referrer" />
                                <div class="play-overlay">
                                    <n-icon :component="CheckmarkCircle" color="#fff" size="24" />
                                </div>
                            </div>
                            
                            <div class="track-info-col">
                                <div class="track-title" :class="{'highlight': item.title === props.song?.title}">
                                    {{ item.title }}
                                </div>
                                <div class="track-meta">
                                    <span class="explicit-tag" :style="{ borderColor: getSourceParams(item.source).color, color: getSourceParams(item.source).color }">
                                        {{ getSourceParams(item.source).label }}
                                    </span>
                                    
                                    <span class="artist-name">{{ item.artist }}</span>
                                    <span class="dot" v-if="item.album">•</span>
                                    <span class="album-name" v-if="item.album">{{ item.album }}</span>
                                    <span class="dot" v-if="item.quality">•</span>
                                    <span class="quality-tag" v-if="item.quality">{{ formatQuality(item.quality) }}</span>
                                </div>
                            </div>

                            <div class="track-time-col">
                                {{ (item.publish_time && item.publish_time.length >= 4) ? item.publish_time.substring(0, 4) : '' }}
                            </div>
                        </div>
                    </div>
                    
                    <div v-else-if="!loading && keyword && hasSearched" class="empty-state">
                        <div class="no-results-text">未找到结果</div>
                        <div class="sub-text">请尝试更换关键词</div>
                    </div>
                </n-spin>
            </div>

            <!-- Step 2: Quality Selection -->
            <div v-else-if="currentStep === 2 && selectedResult" class="selection-view">
                <div class="selection-preview">
                    <div class="preview-cover-wrapper">
                        <img :src="selectedResult.cover_url || '/default-cover.png'" class="preview-cover" referrerpolicy="no-referrer" />
                    </div>
                    <div class="preview-content">
                        <div class="preview-title">{{ selectedResult.title }}</div>
                        <div class="preview-artist">{{ selectedResult.artist }}</div>
                        <div class="preview-album">{{ selectedResult.album }}</div>
                        
                        <div class="quality-selector-block">
                            <div class="section-label">选择音质 (API 实时返回)</div>
                            
                            <n-spin :show="probing" size="small">
                                <template #description>探测中...</template>
                                <div v-if="probedQualities.length > 0">
                                    <n-radio-group v-model:value="selectedQuality" class="quality-radios">
                                        <n-radio-button 
                                            v-for="q in probedQualities" 
                                            :key="q.quality" 
                                            :value="q.quality"
                                        >
                                            <div class="q-btn-content">
                                                <span class="q-label">{{ formatQuality(q.quality) }}</span>
                                                <span class="q-size" v-if="q.size">{{ formatSize(q.size) }}</span>
                                            </div>
                                        </n-radio-button>
                                    </n-radio-group>
                                </div>
                                <div v-else-if="!probing" class="no-quality-msg">
                                     抱歉，该源暂无可下载音质
                                </div>
                                <div v-else style="height: 40px"></div>
                            </n-spin>
                        </div>
                    </div>
                </div>

                <div class="selection-actions">
                    <n-button @click="currentStep = 1" ghost class="back-btn">
                        <template #icon><n-icon :component="ArrowBackOutline"/></template>
                        返回搜索
                    </n-button>
                    <n-button 
                        type="primary" 
                        color="#1db954" 
                        class="download-confirm-btn" 
                        size="large"
                        @click="handleMatch(selectedResult)"
                        :loading="processing"
                        :disabled="probing || probedQualities.length === 0"
                    >
                        <template #icon><n-icon :component="CloudDownloadOutline"/></template>
                        立即下载并替换
                    </n-button>
                </div>
            </div>
        </div>
    </div>
  </n-modal>
</template>

<style scoped>
/* Spotify Modal Styling */
.spotify-modal {
    background-color: #282828;
    color: #fff;
    width: 600px;
    max-width: 90vw;
    border-radius: 8px;
    box-shadow: 0 4px 60px rgba(0,0,0,0.5);
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.modal-header {
    background-color: #121212; /* Darker header */
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    border-bottom: 1px solid #333;
}

.modal-header h3 {
    margin: 0;
    font-size: 24px;
    font-weight: 700;
}

.search-container {
    display: flex;
    gap: 12px;
    align-items: center;
}

.search-input-wrapper {
    flex: 1;
    position: relative;
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 500px;
    height: 38px; /* Reduced height from 48px */
    display: flex;
    align-items: center;
    padding: 0 12px;
    transition: background-color 0.2s;
    border: 1px solid transparent;
}

.search-input-wrapper:hover,
.search-input-wrapper:focus-within {
    background-color: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.5);
}

.search-icon {
    font-size: 20px; /* Smaller icon */
    color: #b3b3b3;
    margin-right: 8px;
}

.spotify-input {
    background: transparent;
    border: none;
    color: #fff;
    font-size: 14px; /* Smaller font */
    width: 100%;
    outline: none;
}
.spotify-input::placeholder {
    color: #b3b3b3;
}

.search-btn {
    height: 38px;
    padding: 0 24px;
    font-weight: 600;
}

.modal-content {
    background-color: #121212;
    padding: 0;
    min-height: 300px;
    max-height: 60vh;
    overflow-y: auto;
}

.stats-bar {
    padding: 12px 24px;
    color: #b3b3b3;
    font-size: 12px;
    border-bottom: 1px solid #282828;
}
.source-stat {
    margin-left: 8px;
    color: #1db954;
}

/* Track List */
.track-list {
    padding: 8px 0;
}

.track-row {
    display: flex;
    align-items: center;
    padding: 8px 16px;
    margin: 0 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.track-row:hover {
    background-color: #2a2a2a;
}
.track-row:hover .play-overlay {
    opacity: 1;
}

.track-img-col {
    position: relative;
    width: 48px;
    height: 48px;
    margin-right: 16px;
}

.track-cover {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 4px;
}

.play-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s;
    border-radius: 4px;
}

.track-info-col {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.track-title {
    font-size: 16px;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 4px;
}
.track-title.highlight {
    color: #1db954; /* Highlight if matches current song title */
}

.track-meta {
    font-size: 14px;
    color: #b3b3b3;
    display: flex;
    align-items: center;
}

.quality-tag {
    font-size: 11px;
    background: #555;
    color: #eee;
    padding: 1px 4px;
    border-radius: 2px;
}

.explicit-tag {
    font-size: 10px;
    border: 1px solid #b3b3b3;
    border-radius: 2px;
    padding: 0 4px;
    margin-right: 6px;
    height: 16px;
    line-height: 14px;
    display: inline-block;
}

.artist-name {
    color: #fff;
}
.artist-name:hover {
    text-decoration: underline;
}

.dot {
    margin: 0 4px;
}

.track-time-col {
    color: #b3b3b3;
    font-size: 14px;
    margin-left: 16px;
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    color: #fff;
}
.no-results-text {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 8px;
}
.sub-text {
    color: #b3b3b3;
}

/* Selection View Step 2 */
.selection-view {
    padding: 32px 24px;
    background: linear-gradient(to bottom, #282828, #121212);
}

.selection-preview {
    display: flex;
    gap: 32px;
    margin-bottom: 40px;
}

.preview-cover-wrapper {
    width: 200px;
    height: 200px;
    flex-shrink: 0;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
}

.preview-cover {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 4px;
}

.preview-content {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.preview-title {
    font-size: 32px;
    font-weight: 800;
    margin-bottom: 8px;
}

.preview-artist {
    font-size: 18px;
    color: #fff;
    margin-bottom: 4px;
}

.preview-album {
    font-size: 14px;
    color: #b3b3b3;
}

.quality-selector-block {
    margin-top: auto;
    min-height: 100px;
}

.quality-radios {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.q-btn-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    line-height: 1.2;
    padding: 4px 0;
}

.q-label {
    font-weight: 700;
}

.q-size {
    font-size: 10px;
    opacity: 0.7;
}

.no-quality-msg {
    color: #ff4d4f;
    font-size: 14px;
}

.section-label {
    font-size: 12px;
    text-transform: uppercase;
    color: #b3b3b3;
    letter-spacing: 0.1em;
    font-weight: 700;
    margin-bottom: 12px;
}

.selection-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 24px;
    border-top: 1px solid #333;
}

.download-confirm-btn {
    padding: 0 40px;
    font-weight: 700;
}

.back-btn {
    border: 1px solid #555;
    color: #fff;
}
.back-btn:hover {
    border-color: #fff !important;
    background: transparent !important;
    color: #fff !important;
}
</style>
