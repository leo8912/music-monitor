<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NSpin, useMessage } from 'naive-ui'
import { SearchOutline, PersonOutline, MusicalNotesOutline, AddOutline, CheckmarkOutline } from '@vicons/ionicons5'
import axios from 'axios'
import type { Artist } from '@/types'

const router = useRouter()
const message = useMessage()

// State
const query = ref('')
const searching = ref(false)
const showDropdown = ref(false)
const searchResults = ref<any[]>([])
const selectedIndex = ref(-1)
const searchContainer = ref<HTMLElement | null>(null)

// Methods
const handleSearch = async () => {
    if (!query.value.trim()) return
    
    searching.value = true
    showDropdown.value = true
    selectedIndex.value = -1

    try {
        const res = await axios.get('/api/discovery/search_artists', {
            params: { keyword: query.value }
        })
        const results = res.data || []
        searchResults.value = deduplicateResults(results)
    } catch (e: any) {
        console.error('Search failed:', e)
        // message.error('搜索失败') 
    } finally {
        searching.value = false
    }
}

// deduplication logic (from AddArtistModal)
const deduplicateResults = (results: any[]) => {
    const map = new Map()
    results.forEach(item => {
        const key = item.name.toLowerCase()
        let currentSources = [item.source]
        let currentIds = { [item.source]: item.id }
        
        if (item.extra_ids) {
            currentSources = Object.keys(item.extra_ids)
            currentIds = { ...item.extra_ids }
        }

        if (map.has(key)) {
            const existing = map.get(key)
            currentSources.forEach(s => {
                if (!existing.sources.includes(s)) existing.sources.push(s)
            })
            existing.extra_ids = { ...existing.extra_ids, ...currentIds }
        } else {
            map.set(key, {
                ...item,
                sources: currentSources,
                extra_ids: currentIds,
                adding: false,
                added: false
            })
        }
    })
    return Array.from(map.values())
}

const addArtist = async (artist: any) => {
    if (artist.adding || artist.added) return
    artist.adding = true

    try {
        const promises = artist.sources.map((source: string) => {
            const sourceId = artist.extra_ids[source] || artist.id
            return axios.post('/api/artists', {
                name: artist.name,
                source: source,
                id: sourceId,
                avatar: artist.avatar
            })
        })
        
        await Promise.all(promises)
        
        message.success(`已关注 ${artist.name}`)
        artist.added = true
        
        // Notify parent to refresh list
        emit('added')
        
        // Clear search after a short delay to allow user to see success state
        setTimeout(() => {
            query.value = ''
            searchResults.value = []
            showDropdown.value = false
        }, 1000)
        
    } catch (e: any) {
        message.error("添加失败: " + (e.response?.data?.detail || e.message))
    } finally {
        artist.adding = false
    }
}

const emit = defineEmits(['added'])

// Click outside to close
const handleClickOutside = (event: MouseEvent) => {
    if (searchContainer.value && !searchContainer.value.contains(event.target as Node)) {
        showDropdown.value = false
    }
}

onMounted(() => {
    document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
})

const handleKeydown = (e: KeyboardEvent) => {
    if (!showDropdown.value) {
        if (e.key === 'Enter') handleSearch()
        return
    }

    if (e.key === 'ArrowDown') {
        e.preventDefault()
        selectedIndex.value = Math.min(selectedIndex.value + 1, searchResults.value.length - 1)
    } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        selectedIndex.value = Math.max(selectedIndex.value - 1, -1)
    } else if (e.key === 'Enter') {
        e.preventDefault()
        if (selectedIndex.value >= 0) {
            addArtist(searchResults.value[selectedIndex.value])
        } else {
            handleSearch()
        }
    } else if (e.key === 'Escape') {
        showDropdown.value = false
    }
}
</script>

<template>
    <div class="global-search" ref="searchContainer">
        <div class="search-input-wrapper" :class="{ active: showDropdown }">
            <n-icon :component="SearchOutline" class="search-icon" />
            <input 
                v-model="query" 
                type="text" 
                placeholder="搜索歌手或歌曲..." 
                @keydown="handleKeydown"
                @focus="showDropdown = searchResults.length > 0"
            />
            <div class="spinner" v-if="searching">
                <n-spin size="small" />
            </div>
        </div>

        <!-- Dropdown Results -->
        <!-- Dropdown Results -->
        <div class="search-dropdown" v-if="showDropdown && (searchResults.length > 0 || searching)">
            <!-- Loading State -->
            <div class="dropdown-loading" v-if="searching">
                <div class="loading-item" v-for="i in 3" :key="i">
                    <div class="skeleton-avatar"></div>
                    <div class="skeleton-info">
                        <div class="skeleton-text w-60"></div>
                        <div class="skeleton-text w-30"></div>
                    </div>
                </div>
            </div>

            <!-- No Results -->
            <div class="dropdown-header" v-else-if="searchResults.length === 0">
                <span class="no-results">未找到结果</span>
            </div>
            
            <!-- Results List -->
            <div class="results-list" v-else>
                <div 
                    v-for="(artist, index) in searchResults" 
                    :key="`${artist.name}-${index}`"
                    class="result-item"
                    :class="{ selected: index === selectedIndex }"
                    @click.stop="addArtist(artist)"
                    @mouseenter="selectedIndex = index"
                >
                    <div class="avatar">
                        <img v-if="artist.avatar" :src="artist.avatar" />
                        <n-icon v-else :component="PersonOutline" />
                    </div>
                    
                    <div class="info">
                        <div class="name">{{ artist.name }}</div>
                        <div class="meta">
                            <span class="source-tag" v-for="s in artist.sources" :key="s" :class="s">
                                {{ s === 'netease' ? '网易' : 'QQ' }}
                            </span>
                        </div>
                    </div>
                    
                    <div class="action">
                        <div v-if="artist.added" class="status-icon success">
                            <n-icon :component="CheckmarkOutline" />
                        </div>
                        <div v-else-if="artist.adding" class="status-icon loading">
                            <n-spin size="small" />
                        </div>
                        <div v-else class="status-icon add">
                            <n-icon :component="AddOutline" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.global-search {
    position: relative;
    width: 360px; /* Fixed width */
    z-index: 100;
}

.search-input-wrapper {
    display: flex;
    align-items: center;
    background: rgba(255, 255, 255, 0.1); /* Dark translucent */
    border-radius: 500px;
    padding: 10px 16px;
    transition: all 0.2s;
    border: 1px solid transparent;
}

.search-input-wrapper:hover {
    background: rgba(255, 255, 255, 0.15);
}

.search-input-wrapper:focus-within,
.search-input-wrapper.active {
    background: #242424;
    border-color: rgba(255, 255, 255, 0.1);
    box-shadow: 0 0 0 1px rgba(255,255,255,0.1);
}

.search-icon {
    font-size: 20px;
    color: #b3b3b3;
    margin-right: 12px;
}

input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: #fff;
    font-size: 14px;
    font-weight: 500;
}

input::placeholder {
    color: #727272;
}

.spinner {
    margin-left: 8px;
    display: flex;
}

/* Dropdown */
.search-dropdown {
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%); /* Center dropdown relative to input */
    width: 400px; /* Wider than input */
    margin-top: 12px;
    background: #242424;
    border-radius: 12px;
    box-shadow: 
        0 20px 40px rgba(0,0,0,0.4),
        0 0 0 1px rgba(255,255,255,0.08);
    padding: 8px;
    max-height: 400px;
    overflow-y: auto;
    z-index: 1000;
}

.dropdown-header {
    padding: 12px;
    text-align: center;
    color: #b3b3b3;
    font-size: 13px;
}

.result-item {
    display: flex;
    align-items: center;
    padding: 10px 16px; /* Larger hit area */
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    gap: 16px;
    width: 100%; /* Ensure full width */
    box-sizing: border-box;
    user-select: none; /* Prevent text selection interfering with click */
}

.result-item:active {
    transform: scale(0.99);
    background: rgba(255,255,255,0.08);
}

.result-item:hover,
.result-item.selected {
    background: rgba(255,255,255,0.12);
}

.avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    overflow: hidden;
    background: #333;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #b3b3b3;
    flex-shrink: 0;
}

.avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.name {
    color: #fff;
    font-size: 15px;
    font-weight: 500;
    margin-bottom: 4px;
}

.meta {
    display: flex;
    gap: 6px;
}

.source-tag {
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 10px;
    color: #000;
    font-weight: 700;
    opacity: 0.8;
}

.source-tag.netease { background-color: #ec4141; color: #fff; }
.source-tag.qqmusic { background-color: #31c27c; color: #fff; }

.action {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
}

.status-icon {
    font-size: 20px;
    display: flex;
    align-items: center;
}


.status-icon.add { color: #b3b3b3; }
.result-item:hover .status-icon.add { color: #fff; }
.status-icon.success { color: #1ed760; }

/* Skeleton Loading */
.dropdown-loading {
    padding: 8px 0;
}

.loading-item {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    gap: 16px;
}

.skeleton-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: rgba(255,255,255,0.06);
    animation: pulse 1.5s infinite;
}

.skeleton-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.skeleton-text {
    height: 12px;
    border-radius: 4px;
    background: rgba(255,255,255,0.06);
    animation: pulse 1.5s infinite;
}

.w-60 { width: 60%; }
.w-30 { width: 30%; }

@keyframes pulse {
    0% { opacity: 0.6; }
    50% { opacity: 1; }
    100% { opacity: 0.6; }
}
</style>
