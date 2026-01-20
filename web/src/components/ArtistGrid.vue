<script setup>
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { RefreshOutline, TrashOutline, AddOutline } from '@vicons/ionicons5'

const props = defineProps({
  artists: { type: Array, default: () => [] },
  selectedArtistName: { type: String, default: null }
})

const emit = defineEmits(['select', 'add', 'update', 'delete'])

const DEFAULT_AVATAR = 'https://p1.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg'

const getArtistAvatar = (artistName) => {
    const found = props.artists.find(a => a.name === artistName)
    if (found && found.avatar) return found.avatar.replace('300x300', '800x800')
    return DEFAULT_AVATAR
}

const handleSelect = (artist) => {
    emit('select', artist)
}

const handleUpdate = (artist) => {
    emit('update', artist)
}

const handleDelete = (artist) => {
    emit('delete', artist)
}

const handleAdd = () => {
    emit('add')
}
</script>

<template>
    <div class="artist-grid-wrapper">
         <div v-for="artist in artists" :key="artist.name" 
              class="artist-item" 
              :class="{ active: selectedArtistName === artist.name }"
              @click="handleSelect(artist)">
              
              <div class="avatar-container">
                  <img :src="getArtistAvatar(artist.name)" class="artist-avatar" loading="lazy" />
                  
                  <!-- Platform Badges (Tiny) -->
                  <div class="platform-badges">
                      <div v-if="artist.sources.includes('netease')" class="badge netease"></div>
                      <div v-if="artist.sources.includes('qqmusic')" class="badge qq"></div>
                  </div>
                  
                  <!-- Hover Overlay -->
                  <div class="avatar-overlay">
                      <div class="overlay-actions">
                          <button class="mini-btn update" @click.stop="handleUpdate(artist)" title="更新">
                              <n-icon><RefreshOutline /></n-icon>
                          </button>
                          <button class="mini-btn delete" @click.stop="handleDelete(artist)" title="删除">
                              <n-icon><TrashOutline /></n-icon>
                          </button>
                      </div>
                  </div>
              </div>
              
              <div class="artist-name">{{ artist.name }}</div>
         </div>
         
         <!-- Add Item (Quick Access) -->
         <div class="artist-item add-item" @click="handleAdd">
             <div class="avatar-container add-placeholder-img">
                <img :src="DEFAULT_AVATAR" class="artist-avatar" />
                <div class="add-icon-overlay">
                     <n-icon size="32"><AddOutline /></n-icon>
                </div>
             </div>
             <div class="artist-name">添加</div>
         </div>
    </div>
</template>

<style scoped>
.artist-grid-wrapper {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 32px 36px;
    margin-bottom: 60px;
}
.artist-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
    transition: transform 0.2s ease;
}
.artist-item:hover {
    transform: translateY(-4px);
}
.avatar-container {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    position: relative;
    margin-bottom: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08); /* Softer shadow */
    background: #fff;
}
.artist-avatar {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    object-fit: cover;
    transition: filter 0.2s;
}
.artist-item.active .artist-avatar {
    box-shadow: 0 0 0 3px var(--accent-primary);
}
.platform-badges {
    position: absolute;
    bottom: 4px;
    right: 4px;
    display: flex;
    gap: -4px;
}
.badge {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid #fff;
}
.badge.netease { background: var(--accent-netease); z-index: 2; }
.badge.qq { background: var(--accent-qq); z-index: 1; margin-left: -4px; }

/* Artist Hover Actions */
.avatar-overlay {
    position: absolute;
    top: 0; left: 0;right: 0; bottom: 0;
    border-radius: 50%;
    background: rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s;
    backdrop-filter: blur(2px);
}
.artist-item:hover .avatar-overlay {
    opacity: 1;
}
.overlay-actions {
    display: flex;
    gap: 8px;
}
.mini-btn {
    border: none;
    background: rgba(255,255,255,0.9);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    color: #333;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 16px;
    transition: transform 0.1s;
}
.mini-btn:hover { transform: scale(1.1); background: #fff; }
.mini-btn.delete { color: var(--accent-primary); }

.artist-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
    text-align: center;
    width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Add Item & Overlay Specifics */
.add-placeholder-img {
    position: relative;
    cursor: pointer;
    transition: transform 0.2s;
}
.add-icon-overlay {
    position: absolute;
    top:0; left:0; right:0; bottom:0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    opacity: 0;
    transition: opacity 0.2s;
}
.artist-item.add-item:hover .add-icon-overlay {
    opacity: 1;
}
.artist-item.add-item:hover .avatar-container {
    transform: scale(1.08); /* Pop a bit more */
    box-shadow: 0 8px 16px rgba(0,0,0,0.12);
}

/* 深色模式 */
:root[data-theme="dark"] .avatar-container {
    background: #2C2C2E;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
:root[data-theme="dark"] .badge {
    border-color: #1C1C1E;
}
:root[data-theme="dark"] .mini-btn {
    background: rgba(255,255,255,0.15);
    color: #f5f5f7;
}
:root[data-theme="dark"] .mini-btn:hover {
    background: rgba(255,255,255,0.25);
}
</style>
