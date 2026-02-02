<template>
    <div class="artist-grid">
         <!-- Loading Skeletons -->
         <template v-if="loading">
             <div v-for="i in 6" :key="`skel-${i}`" class="artist-card skeleton-card">
                 <div class="avatar-box skeleton-box">
                    <Skeleton shape="circle" width="100%" height="100%" />
                 </div>
                 <div class="info">
                    <Skeleton width="60%" height="16px" style="margin-bottom: 8px" />
                    <Skeleton width="40%" height="12px" />
                 </div>
             </div>
         </template>

         <template v-else>
            <!-- 歌手卡片 -->
            <div v-for="artist in artists" :key="artist.name" 
                class="artist-card clickable" 
                :class="{ active: selectedArtistName === artist.name }"
                @click="handleArtistClick(artist)">
                
                <div class="avatar-box" :class="{ 'updating': isUpdating(artist) }">
                    <img :src="getArtistAvatar(artist.name)" class="avatar" loading="lazy" />
                    
                    <!-- 刷新状态覆盖层 (Minimalist) -->
                    <div v-if="isUpdating(artist)" class="loading-overlay minimalist">
                        <n-spin size="small" stroke="#1DB954" />
                    </div>

                    <!-- 悬浮操作 (非刷新时显示) -->
                    <div v-else class="overlay">
                        <div class="actions">
                            <button class="action-btn" @click.stop="emit('update', artist)" title="刷新同步">
                                <n-icon :component="RefreshOutline" />
                            </button>
                            <button class="action-btn delete" @click.stop="emit('delete', artist)" title="取消关注">
                                <n-icon :component="TrashOutline" />
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="info">
                    <div class="name-row">
                        <div class="name truncate">{{ artist.name }}</div>
                        <!-- Platform Badges (Moved here for visibility) -->
                        <div class="badges">
                            <div v-if="artist.sources.includes('netease')" class="badge netease" title="网易云音乐"></div>
                            <div v-if="artist.sources.includes('qqmusic')" class="badge qq" title="QQ音乐"></div>
                        </div>
                    </div>
                    <div class="subtitle" :class="{ 'text-green': isUpdating(artist) }">
                        <span v-if="isUpdating(artist)" class="status-text">
                            {{ getStatusText(artist) }}
                        </span>
                        <span v-else>{{ artist.songCount || 0 }} 首歌曲</span>
                    </div>
                </div>
            </div>
         </template>
    </div>
</template>

<script setup lang="ts">
/**
 * 歌手网格组件 - Refined Spotify Style
 */
import { useRouter } from 'vue-router'
import { NIcon, NSpin } from 'naive-ui'
import { RefreshOutline, TrashOutline, AddOutline } from '@vicons/ionicons5'
import Skeleton from '@/components/common/Skeleton.vue'
import { useProgressStore } from '@/stores/progress'

const router = useRouter()
const progressStore = useProgressStore()

const props = defineProps({
  artists: { type: Array as () => any[], default: () => [] },
  selectedArtistName: { type: String, default: null },
  loading: { type: Boolean, default: false },
  refreshingArtistName: { type: String, default: null }
})

const emit = defineEmits(['select', 'add', 'update', 'delete'])

const DEFAULT_AVATAR = 'https://p1.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg'

const getArtistAvatar = (artistName: string) => {
    const found = props.artists.find(a => a.name === artistName)
    if (found && found.avatar) return found.avatar.replace('300x300', '800x800')
    return DEFAULT_AVATAR
}

const getProgress = (artist: any) => {
    const id = artist.id || (artist.ids && artist.ids[0]?.id)
    return progressStore.getProgress(id)
}

const isUpdating = (artist: any) => {
    return !!getProgress(artist) || props.refreshingArtistName === artist.name
}

const getStatusText = (artist: any) => {
    const p = getProgress(artist)
    if (p) return p.message || "更新中..."
    return "准备中..."
}

const isMobile = () => /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)

const handleArtistClick = (artist: any) => {
    const artistId = artist.id || (artist.ids && artist.ids[0]?.id)
    if (!artistId) return
    
    if (isMobile()) {
        router.push(`/mobile/artist/${artistId}`)
    } else {
        router.push(`/artist/${artistId}`)
    }
}
</script>

<style scoped>
.artist-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 24px 20px;
    padding: 16px 0;
}

.artist-card {
    padding: 16px;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    transition: background-color 0.3s ease;
    cursor: pointer;
}

.artist-card:hover {
    background-color: var(--sp-card-hover);
}

.artist-card.active {
    background-color: var(--sp-highlight);
}

/* Avatar Box */
.avatar-box {
    width: 140px;
    height: 140px;
    border-radius: 50%;
    position: relative;
    margin-bottom: 12px;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    background-color: var(--sp-card);
    transition: box-shadow 0.3s ease, transform 0.3s ease;
}

.avatar-box.updating {
    box-shadow: 0 0 0 2px rgba(29, 185, 84, 0.5);
    animation: pulse-green 2s infinite;
}

@keyframes pulse-green {
    0% { box-shadow: 0 0 0 0 rgba(29, 185, 84, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(29, 185, 84, 0); }
    100% { box-shadow: 0 0 0 0 rgba(29, 185, 84, 0); }
}

.artist-card:hover .avatar-box {
    /* If updating, don't override with standard hover shadow? keep pulse? */
    transform: translateY(-2px);
}
.artist-card:hover .avatar-box:not(.updating) {
    box-shadow: 0 12px 32px rgba(0,0,0,0.6);
}

.avatar {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: opacity 0.3s;
}

/* Loading Overlay */
.loading-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
}

.loading-overlay.minimalist {
    background: rgba(0,0,0,0.3);
    backdrop-filter: blur(1px);
}

/* Info Section */
.info {
    width: 100%;
    text-align: center;
}

.name-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    margin-bottom: 4px;
}

.name {
    font-size: 16px;
    font-weight: 700;
    color: var(--text-primary);
    max-width: 120px;
}

.subtitle {
    font-size: 13px;
    color: var(--text-secondary);
    min-height: 19px; /* Avoid jump */
}

.subtitle.text-green {
    color: var(--sp-green);
    font-weight: 500;
    font-size: 12px;
}
.status-text {
    animation: fade-in 0.3s ease;
}
@keyframes fade-in {
    from { opacity: 0; transform: translateY(2px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Badges */
.badges {
    display: flex;
    gap: 3px;
    flex-shrink: 0;
}

.badge {
    width: 6px;
    height: 6px;
    border-radius: 50%;
}
.badge.netease { background-color: #ec4141; box-shadow: 0 0 4px #ec4141; }
.badge.qq { background-color: #2daf71; box-shadow: 0 0 4px #2daf71; }

/* Overlay Actions */
.overlay {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s ease;
    backdrop-filter: blur(2px);
}

.artist-card:hover .overlay {
    opacity: 1;
}

.actions { display: flex; gap: 16px; }

.action-btn {
    width: 40px; height: 40px;
    border-radius: 50%;
    background: transparent;
    border: 1px solid rgba(255,255,255,0.6);
    color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    cursor: pointer;
    transition: all 0.2s;
}

.action-btn:hover {
    background: #fff;
    color: #000;
    border-color: #fff;
    transform: scale(1.1);
}

.action-btn.delete:hover {
    background: #ff3b30;
    border-color: #ff3b30;
    color: #fff;
}
</style>
