<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import axios from 'axios'
import { useMessage, NIcon } from 'naive-ui'
import {
  RefreshOutline, PersonCircleOutline, SettingsOutline, AddOutline,
  MoonOutline, SunnyOutline
} from '@vicons/ionicons5'
import { saveTheme, themeMode } from './utils/theme'

// Components
import BottomPlayer from './components/BottomPlayer.vue'
import ArtistGrid from './components/ArtistGrid.vue'
import SongList from './components/SongList.vue'
import SettingsModal from './components/settings/SettingsModalV2.vue'
import ProfileModal from './components/ProfileModal.vue'
import AddArtistModal from './components/AddArtistModal.vue'
import UserDropdown from './components/UserDropdown.vue'
import RepairModal from './components/RepairModal.vue'

const message = useMessage()

// State
const rawArtists = ref([]) 
const history = ref([])
// const isDark = ref(false) - Removed, using global themeMode
const loading = ref(false)
const loadingHistory = ref(false)
const sysStatus = ref('')
const nextRunTime = ref(null)
const oneWord = ref('')

// Player State
const currentAudioUrl = ref('')
const currentSong = ref({})
const isPlayerLoading = ref(false)
const isDark = ref(false) // Theme toggle state

// UI State
const selectedArtistName = ref(null) 
const showAddModal = ref(false)
const showSettingsModal = ref(false)
const showProfileModal = ref(false)
const showRepairModal = ref(false)

// User State
const user = ref({ username: 'My Music', avatar: '' })

const fetchUser = async () => {
    try {
        const res = await axios.get('/api/check_auth')
        if (res.data.authenticated) {
            user.value.username = res.data.user
            user.value.avatar = res.data.avatar
        }
    } catch (e) {
        // console.warn("Fetch user failed")
    }
}

const handleLogout = async () => {
    try {
        await axios.post('/api/logout')
        message.success("已退出登录")
        setTimeout(() => window.location.href = '/login', 500)
    } catch (e) {
        message.error("退出失败")
    }
}

// 1. Artists Logic
const mergedArtists = computed(() => {
    const map = new Map()
    rawArtists.value.forEach(a => {
        if (!map.has(a.name)) {
            map.set(a.name, {
                name: a.name,
                sources: [],
                ids: [],
                avatar: ''
            })
        }
        const entry = map.get(a.name)
        entry.sources.push(a.source)
        entry.ids.push({ source: a.source, id: a.id })
        if (!entry.avatar && a.avatar) entry.avatar = a.avatar
    })
    return Array.from(map.values())
})

const fetchArtists = async () => {
    try {
        const res = await axios.get('/api/artists')
        rawArtists.value = res.data
    } catch (e) {
        console.error(e)
    }
}

const selectArtist = (artist) => {
    if (selectedArtistName.value === artist.name) {
        selectedArtistName.value = null // Toggle off
    } else {
        selectedArtistName.value = artist.name
        fetchHistory()
    }
}
// Note: selectArtist now calls fetchHistory inside block? or watch?
// In Step 1061 it was:
// selectArtist... then fetchHistory() outside if/else?
// "selectArtist = (artist) => { ... fetchHistory() }"
// My previous code:
// if (...) null else name;
// fetchHistory()
// Correct. I fixed indentation in this version.

const deleteMergedArtist = async (artist) => {
    try {
        // Optimistic update
        rawArtists.value = rawArtists.value.filter(a => a.name !== artist.name)
        if (selectedArtistName.value === artist.name) selectedArtistName.value = null
        
        for (const item of artist.ids) {
            await axios.delete(`/api/artists/${item.source}/${item.id}`)
        }
        await fetchArtists() // Sync
        fetchHistory()
        message.success(`已删除 ${artist.name}`)
    } catch (e) {
        message.error("删除失败")
        fetchArtists() // Revert
    }
}

const triggerCheck = async (artist) => {
    message.loading(`正在扫描 ${artist.name}...`)
    try {
        await Promise.all(artist.sources.map(s => axios.post(`/api/check/${s}`)))
        message.success(`扫描完成`)
        fetchHistory()
    } catch (e) {
        message.error("扫描触发失败")
    }
}

// 2. History & Feed Logic
const fetchHistory = async () => {
  loadingHistory.value = true
  try {
    const params = {}
    if (selectedArtistName.value) {
        params.author = selectedArtistName.value
    }
    const res = await axios.get('/api/history', { params })
    history.value = res.data.map(item => ({
      ...item,
      publish_time: item.publish_time
    }))
  } catch (e) {
    console.error(e)
  } finally {
      loadingHistory.value = false
  }
}

const fetchOneWord = async () => {
    try {
        const res = await axios.get('https://v1.hitokoto.cn/?c=i&c=d&c=k')
        oneWord.value = `“${res.data.hitokoto}”`
    } catch (e) {
        oneWord.value = '“生活不止眼前的苟且，还有诗和远方”'
    }
}

// 3. Player Logic
const handlePlay = async (song) => {
    isPlayerLoading.value = true // Start loading
    // 立即设置当前歌曲，确保 Dock 提前弹出
    currentSong.value = song
    
    // 播放本地音频文件
    // 1. 检查是否有本地缓存
    if (song.local_audio_path) {
        // 有缓存,直接播放
        const audioUrl = `/api/audio/${encodeURIComponent(song.local_audio_path)}?t=${Date.now()}`
        // currentSong.value = song // Removed: already set above
        currentAudioUrl.value = audioUrl
        message.success('正在播放 ▶️')
        isPlayerLoading.value = false // End loading
    } else {
        // 无缓存,自动下载
        message.loading('正在下载音频...')
        try {
            const res = await axios.post('/api/download_audio', {
                source: song.source,
                song_id: song.media_id,
                title: song.title,
                artist: song.author,
                album: song.album || '',
                pic_url: song.cover || ''
            })
            
            if (res.data.local_path) {
                // 下载成功,播放
                const audioUrl = `/api/audio/${encodeURIComponent(res.data.local_path)}?t=${Date.now()}`
                
                // 更新歌曲记录（本地乐观更新）
                song.local_audio_path = res.data.local_path
                song.audio_quality = res.data.quality
                
                // currentSong.value = song // Removed: already set above
                currentAudioUrl.value = audioUrl
                
                message.success(`下载完成,正在播放 (${res.data.quality}k) ▶️`)
            } else {
                message.error('下载失败')
            }
        } catch (e) {
            console.error(e)
            message.error('下载失败: ' + (e.response?.data?.detail || e.message))
        } finally {
            isPlayerLoading.value = false // End loading
        }
    }
}

const handlePrev = () => {
     if (!currentSong.value || !history.value || !history.value.length) return
     let idx = history.value.findIndex(res => res.unique_key === currentSong.value.unique_key)
     if (idx < 0 && currentSong.value.media_id) idx = history.value.findIndex(res => res.media_id === currentSong.value.media_id && res.source === currentSong.value.source)
     
     if (idx < 0) { handlePlay(history.value[0]); return }
     
     let prevIdx = idx - 1
     if (prevIdx < 0) prevIdx = history.value.length - 1
     handlePlay(history.value[prevIdx])
}

const handleNext = () => {
     if (!currentSong.value || !history.value || !history.value.length) return
     let idx = history.value.findIndex(res => res.unique_key === currentSong.value.unique_key)
     if (idx < 0) idx = history.value.findIndex(res => res.media_id === currentSong.value.media_id && res.source === currentSong.value.source)
     
     let nextIdx = idx + 1
     if (nextIdx >= history.value.length) nextIdx = 0
     handlePlay(history.value[nextIdx])
}

const handleError = () => {
     isPlayerLoading.value = false // End loading
     // Auto-repair logic on frontend
     if (currentSong.value && currentSong.value.local_audio_path) {
         message.warning("检测到文件丢失，正在自动重新下载...")
         // Clear local cache state
         currentSong.value.local_audio_path = null
         currentSong.value.audio_quality = null
         // Retry play (triggers download)
         handlePlay(currentSong.value)
     } else {
         message.error("播放失败")
     }
}


const handleToggleFavorite = async () => {
    if (!currentSong.value) return
    const song = currentSong.value
    // Optimistic Update
    const originalState = song.is_favorite
    song.is_favorite = !originalState
    
    // API Call
    try {
        const res = await axios.post('/api/favorites/toggle', {
            source: song.source,
            song_id: song.media_id,
            title: song.title,
            artist: song.author || song.artist,
            album: song.album,
            pic_url: song.cover || song.cover_url
        })
        if (res.data.success) {
            message.success(res.data.state ? '已添加收藏 ❤️' : '已取消收藏')
            song.is_favorite = res.data.state
            // Sync history list state if present
            if (history.value) {
                const historyItem = history.value.find(h => h.unique_key === song.unique_key)
                if (historyItem) historyItem.is_favorite = res.data.state
            }
        } else {
             message.error(res.data.message || '操作失败')
             song.is_favorite = originalState // Revert
        }
    } catch (e) {
        message.error('操作失败')
        song.is_favorite = originalState // Revert
    }
}

// 4. System Logic
const triggerScan = async () => {
    loading.value = true
    message.loading('开始全局同步...')
    try {
        const plugins = ['netease', 'qqmusic']
        await Promise.all(plugins.map(p => axios.post(`/api/check/${p}`)))
        message.success('全局同步完成')
        fetchHistory()
    } catch (e) {
        message.error('扫描失败')
    } finally {
        loading.value = false
    }
}

const fetchStatus = async () => {
    try {
        const res = await axios.get('/api/status')
        if (res.data.jobs && res.data.jobs.length > 0) {
            // Find earliest next run
            const jobs = res.data.jobs.filter(j => j.next_run)
            if (jobs.length > 0) {
                jobs.sort((a, b) => new Date(a.next_run) - new Date(b.next_run))
                nextRunTime.value = jobs[0].next_run
                updateStatusText()
            }
        }
    } catch (e) { console.error(e) }
}

const updateStatusText = () => {
    if (!nextRunTime.value) return
    const now = new Date()
    const diff = new Date(nextRunTime.value) - now
    if (diff > 0) {
        const min = Math.ceil(diff / 60000)
        sysStatus.value = `⏱️ 下次同步: ${min}分钟后`
    } else {
        sysStatus.value = '🔄 正在同步中...'
    }
}

// Helper to toggle theme
const toggleTheme = () => {
    const newTheme = themeMode.value === 'dark' ? 'light' : 'dark'
    saveTheme(newTheme)
    axios.post('/api/settings', {
        global: { theme: newTheme }
    }).catch(e => console.warn('Theme sync failed:', e))
}

// Lifecycle
onMounted(async () => {
  // Theme is handled globally by App.vue calling initTheme()

  fetchUser() // Fetch user info
  await fetchArtists()
  await fetchHistory()
  await fetchStatus()
  fetchOneWord()
  setInterval(updateStatusText, 60000)

  // Check for deep link params
  const params = new URLSearchParams(window.location.search)
  const source = params.get('source')
  const songId = params.get('songId')

  if (source && songId) {
      // Find in history first (fastest)
      let song = history.value.find(s => s.source === source && s.media_id === songId)
      
      if (song) {
          message.info('正在跳转到目标歌曲...')
          handlePlay(song)
          // Clean URL
          window.history.replaceState({}, '', '/')
      } else {
          console.warn("Deep link song not found in recent history")
      }
  }

  // Check for artist deep link (from notification)
  const deepArtist = params.get('artist') || params.get('author')
  if (deepArtist) {
      // Wait for artists to load
      const exists = mergedArtists.value.find(a => a.name === deepArtist)
      if (exists) {
          selectArtist(exists)
          message.info(`已定位到歌手: ${deepArtist}`)
          window.history.replaceState({}, '', '/')
      }
  }
})

</script>

<template>
    <div class="app-container">
        <!-- Header -->
        <header class="app-header">
            <div class="header-content">
                <div class="brand-section">
                    <h1>🎵 Music Monitor</h1>
                    <p class="status-subtitle" v-if="sysStatus">
                        <span class="status-dot-status"></span>
                        {{ sysStatus }}
                    </p>
                </div>
                <div class="nav-buttons">
                    <!-- Primary Action -->
                    <button class="nav-btn primary" @click="showAddModal = true" title="添加订阅" style="margin-right: 8px;">
                         <n-icon size="20"><AddOutline /></n-icon>
                         <span class="btn-text">添加订阅</span>
                    </button>

                    <!-- Tools -->
                    <div class="tool-group">
                        <button class="nav-btn" :class="{ spinning: loading }" @click="triggerScan" title="立即同步">
                            <n-icon size="20"><RefreshOutline /></n-icon>
                        </button>
                        <button class="nav-btn" @click="toggleTheme" :title="themeMode === 'dark' ? '切换浅色' : '切换深色'">
                            <n-icon size="20">
                                <SunnyOutline v-if="themeMode === 'dark'" />
                                <MoonOutline v-else />
                            </n-icon>
                        </button>
                    </div>

                    <!-- User Menu -->
                    <UserDropdown 
                        :username="user?.username || 'My Music'"
                        :avatar="user?.avatar"
                        @open-settings="showSettingsModal = true"
                        @open-profile="showProfileModal = true"
                        @logout="handleLogout"
                    />
                </div>
            </div>
        </header>

        <!-- Components -->
        <ArtistGrid 
            :artists="mergedArtists" 
            :selected-artist-name="selectedArtistName"
            @select="selectArtist"
            @update="triggerCheck"
            @delete="deleteMergedArtist"
            @add="showAddModal = true"
        />

        <SongList 
            :history="history"
            :loading="loadingHistory"
            :selected-artist-name="selectedArtistName"
            :one-word="oneWord"
            @play="handlePlay"
            @clear-filter="selectArtist({name: selectedArtistName})"
        />

        <!-- Modals -->
        <SettingsModal v-model:show="showSettingsModal" />
        <ProfileModal 
            v-model:show="showProfileModal" 
            @profile-updated="(data) => {
                if (data.username) user.username = data.username
                if (data.avatar) user.avatar = data.avatar
            }"
        />
        <AddArtistModal v-model:show="showAddModal" @added="fetchArtists" />
        <RepairModal v-if="currentSong?.title" v-model:show="showRepairModal" :song-info="currentSong" @repaired="(data) => {
            currentSong.local_audio_path = data.local_path;
            currentSong.audio_quality = data.quality;
            handlePlay(currentSong);
        }" />

        <!-- Bottom Dock Player -->
        <BottomPlayer 
            :audioUrl="currentAudioUrl"
            :info="currentSong"
            :source="currentSong.source"
            :mediaId="currentSong.media_id"
            :isLoading="isPlayerLoading"
            @prev="handlePrev"
            @next="handleNext"
            @ended="handleNext"
            @error="handleError"
            @repair="showRepairModal = true"
            @toggle-favorite="handleToggleFavorite"
        />

    </div>
</template>

<style scoped>
/* App Layout */
.app-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px 120px; /* Bottom padding for player */
}

/* Header */
.app-header {
    padding: 60px 0 40px;
}
.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.app-header h1 {
    font-size: 34px;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: -0.025em;
    margin-right: 16px;
    font-family: var(--font-sans);
}
.brand-section {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
}
.status-subtitle {
    display: flex;
    align-items: center;
    font-size: 14px;
    color: var(--text-secondary);
    gap: 6px;
    margin: 0;
    font-weight: 400;
}
.status-dot-status {
    width: 6px; height: 6px; background: #34C759; border-radius: 50%;
    box-shadow: 0 0 0 2px rgba(52, 199, 89, 0.2);
}

/* Header Actions */
.header-actions {
    display: flex;
    gap: 12px;
}
.nav-btn {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
    background-color: transparent; /* Transparent default */
    color: var(--text-primary);
    /* backdrop-filter: blur(10px); Removed blur for cleaner look */
}
.nav-btn:hover {
    background-color: var(--bg-card);
    box-shadow: var(--shadow-sm);
    transform: scale(1.05);
}
.nav-btn.primary {
    background-color: var(--accent-primary);
    color: #fff;
    box-shadow: 0 4px 12px rgba(250, 45, 72, 0.3);
}
.nav-btn.primary:hover {
    background-color: #d61e35;
    transform: scale(1.05);
}
.nav-btn.spinning n-icon {
    animation: spin 1s linear infinite;
}
@keyframes spin { 100% { transform: rotate(360deg); } }

/* 深色模式调整 */
:root[data-theme="dark"] .nav-btn {
    background-color: transparent;
}
:root[data-theme="dark"] .nav-btn:hover {
    background-color: rgba(255, 255, 255, 0.12);
}

/* Fade List Transition */
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
/* Header Layout */
.nav-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
}

.tool-group {
    display: flex;
    align-items: center;
    gap: 12px;
}

.divider {
    /* Removed divider for cleaner look */
    display: none;
}

.btn-text {
    font-size: 14px;
    font-weight: 600;
    margin-left: 6px;
}

.nav-btn.primary {
    padding: 0 16px;
    height: 36px;
    border-radius: 18px;
    background: var(--primary-color, #FA233B);
    color: white;
    width: auto; /* Override square width */
}

.nav-btn.primary:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 12px rgba(250, 35, 59, 0.3);
}

/* Dark Mode Adapts */
:root[data-theme="dark"] .tool-group {
    background: transparent; /* Fix boxy background */
}

:root[data-theme="dark"] .divider {
    background: rgba(255, 255, 255, 0.15);
}
</style>
