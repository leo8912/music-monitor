<script setup lang="ts">
import { h } from 'vue'
import { NIcon, NEmpty, NButton, useMessage } from 'naive-ui'
import { CloudDownloadOutline } from '@vicons/ionicons5'
import Skeleton from '@/components/common/Skeleton.vue'

const props = defineProps({
  items: { type: Array as () => any[], default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['download'])
const message = useMessage()

const handleDownload = (item: any) => {
    emit('download', item)
}

const formatSize = (sizeStr: string) => {
    return sizeStr || ''
}

const getQualityColor = (quality: any) => {
    const q = parseInt(String(quality))
    if (q >= 2000) return '#c0392b' // Hi-Res
    if (q >= 1000) return '#f1c40f' // Flac
    if (q >= 320) return '#20d25c' // 320k
    return '#3498db'
}

const getQualityLabel = (quality: any) => {
     const q = parseInt(String(quality))
    if (q >= 2000) return 'HR'
    if (q >= 1000) return 'SQ'
    if (q >= 320) return 'HQ'
    return 'PQ'
}

</script>

<template>
  <div class="download-list">
    <!-- Header -->
    <div class="list-header">
        <div class="col-index">#</div>
        <div class="col-title">标题</div>
        <div class="col-artist">歌手</div>
        <div class="col-album">专辑</div>
        <div class="col-quality">音质</div>
        <div class="col-action"></div>
    </div>

    <!-- Items -->
    <template v-if="loading">
        <div v-for="i in 10" :key="`skel-${i}`" class="list-item">
            <div class="col-index"><Skeleton width="16px" height="16px" shape="text" /></div>
            
            <div class="col-title">
                <div class="song-cover-wrapper">
                    <Skeleton width="100%" height="100%" />
                </div>
                <div style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
                     <Skeleton width="60%" height="16px" />
                </div>
            </div>
            
            <div class="col-artist"><Skeleton width="50%" height="14px" /></div>
            <div class="col-album"><Skeleton width="70%" height="14px" /></div>
            
            <div class="col-quality">
                 <Skeleton width="30px" height="16px" />
            </div>
            
            <div class="col-action">
                <Skeleton width="60px" height="28px" />
            </div>
        </div>
    </template>

    <template v-else-if="items.length > 0">
        <div v-for="(item, index) in items" :key="item.id" class="list-item">
            <div class="col-index">{{ index + 1 }}</div>
            
            <div class="col-title">
                <div class="song-cover-wrapper">
                    <img :src="item.cover_url || '/default-cover.png'" class="song-cover" loading="lazy" />
                     <div class="source-badge" :class="item.source">{{ item.source }}</div>
                </div>
                <span class="title-text truncate" :title="item.title">{{ item.title }}</span>
            </div>
            
            <div class="col-artist truncate">{{ item.artist }}</div>
            <div class="col-album truncate">{{ item.album }}</div>
            
            <div class="col-quality">
                 <div class="quality-badge" :style="{ borderColor: getQualityColor(item.quality), color: getQualityColor(item.quality) }">
                    {{ getQualityLabel(item.quality) }}
                    <span class="size-text" v-if="item.size">{{ item.size }}</span>
                 </div>
            </div>
            
            <div class="col-action">
                <n-button 
                    size="small" 
                    secondary 
                    type="primary" 
                    class="download-btn" 
                    :loading="item._loading"
                    :disabled="item._loading"
                    @click="handleDownload(item)"
                >
                    <template #icon>
                        <n-icon :component="CloudDownloadOutline" />
                    </template>
                    {{ item._loading ? '下载中' : '下载' }}
                </n-button>
            </div>
        </div>
    </template>
    
    <div v-else class="empty-state">
        <n-empty description="输入关键词以搜索资源" />
    </div>
  </div>
</template>

<style scoped>
.download-list {
    width: 100%;
}

.list-header, .list-item {
    display: grid;
    grid-template-columns: 40px 4fr 3fr 3fr 120px 100px;
    gap: 16px;
    align-items: center;
    padding: 12px 16px;
}

.list-header {
    border-bottom: 1px solid rgba(255,255,255,0.1);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
}

.list-item {
    border-radius: 8px;
    transition: background 0.2s;
    margin-bottom: 4px;
}

.list-item:hover {
    background: rgba(255,255,255,0.05);
}

.col-index { color: var(--text-secondary); text-align: center; font-variant-numeric: tabular-nums; }
.col-title { display: flex; align-items: center; gap: 12px; font-weight: 500; color: #fff; overflow: hidden; }
.col-artist { color: var(--text-secondary); font-size: 13px; }
.col-album { color: var(--text-secondary); font-size: 13px; }

.song-cover-wrapper {
    position: relative;
    width: 40px; height: 40px;
    flex-shrink: 0;
}
.song-cover {
    width: 100%; height: 100%; border-radius: 4px; object-fit: cover;
    background: #333;
}
.source-badge {
    position: absolute; bottom: -2px; right: -4px;
    font-size: 9px; padding: 1px 3px; border-radius: 2px;
    background: #444; color: #ccc;
    text-transform: uppercase;
    transform: scale(0.8);
}
.source-badge.netease { background: #c20c0c; color: #fff; }
.source-badge.qqmusic { background: #20d25c; color: #000; }
.source-badge.kuwo { background: #f1c40f; color: #000; }
.source-badge.migu { background: #e91e63; color: #fff; }

.quality-badge {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    font-size: 10px;
    font-weight: bold;
    border: 1px solid #555;
    padding: 2px 6px;
    border-radius: 4px;
    line-height: 1.2;
}
.size-text {
    font-size: 9px; opacity: 0.8; font-weight: normal;
}

.truncate {
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.empty-state {
    padding: 60px 0;
    display: flex; justify-content: center;
}
</style>
