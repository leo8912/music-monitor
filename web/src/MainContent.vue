
<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import axios from 'axios'
import { 
  NGrid, NGridItem, NButton, NAvatar, NModal, NInput, NIcon, NSpin, NEmpty, useMessage,
  NSwitch, NInputNumber, NSelect, NTabs, NTabPane
} from 'naive-ui'
import { 
  TrashOutline, SearchOutline, AddOutline, RefreshOutline, PlayCircleOutline, 
  LogoGithub, CheckmarkCircleOutline,
  CloseOutline, SettingsOutline, PersonCircleOutline, LogOutOutline
} from '@vicons/ionicons5'


const message = useMessage()
const rawArtists = ref([]) 
const history = ref([])
// ...
const logs = ref([])
const refreshingLogs = ref(false)
const logContainer = ref(null)
const activeSettingsTab = ref('monitor') // Bind to n-tabs
let logPoller = null

// 1. fetchLogs (Moved UP for hoisting)
const fetchLogs = async () => {
    // refreshingLogs.value = true // Don't show loading spinner on auto-poll to avoid flicker
    try {
        const res = await axios.get('/api/logs')
        
        // Smart Scroll Logic
        let shouldScroll = false
        if (logContainer.value) {
            const el = logContainer.value
            if (el.scrollHeight - el.scrollTop - el.clientHeight < 50) {
                shouldScroll = true
            }
        }
        
        logs.value = res.data
        
        if (shouldScroll) {
            nextTick(() => {
                if (logContainer.value) {
                    logContainer.value.scrollTop = logContainer.value.scrollHeight
                }
            })
        }
    } catch (e) {} finally {
        refreshingLogs.value = false
    }
}

// 2. Log Polling Logic
const startLogPolling = () => {
    stopLogPolling()
    fetchLogs() // Immediate fetch
    logPoller = setInterval(fetchLogs, 2000)
}

const stopLogPolling = () => {
    if (logPoller) {
        clearInterval(logPoller)
        logPoller = null
    }
}

const selectedArtistName = ref(null) 
const showAddModal = ref(false)
const newArtistName = ref('')
const adding = ref(false)
const loading = ref(false)
const loadingHistory = ref(false)
const sysStatus = ref('')
const nextRunTime = ref(null)
const showVideoModal = ref(false)
const currentBvid = ref(null)

// Settings State
const showSettingsModal = ref(false)
const savingSettings = ref(false)
const testingNotify = ref(null) // 'wecom' | 'telegram' | null
const settingsForm = ref({
    global: { check_interval_minutes: 60, log_level: 'INFO' },
    monitor: {},
    notify: { wecom: {}, telegram: {} }
})
const logOptions = [
    { label: 'INFO', value: 'INFO' },
    { label: 'DEBUG', value: 'DEBUG' },
    { label: 'WARNING', value: 'WARNING' }
]

const getServiceName = (key) => {
    const maps = { 'netease': '网易云音乐', 'qqmusic': 'QQ 音乐', 'bilibili': 'Bilibili' }
    return maps[key] || key
}

// Notification UI State
const activeNotifyChannel = ref('wecom')
const channelConfig = computed(() => settingsForm.value.notify[activeNotifyChannel.value])
const checkingStatus = ref(false)
const channelStatus = ref({ wecom: null, telegram: null }) // null=unknown, true=ok, false=error

const checkChannelStatus = async (channel) => {
    checkingStatus.value = true
    try {
        // save first
        await axios.post('/api/settings', settingsForm.value)
        const res = await axios.get(`/api/check_notify_status/${channel}`)
        channelStatus.value[channel] = res.data.connected
        if (res.data.connected) {
            message.success(`${channel === 'wecom' ? '企业微信' : 'Telegram'} 连接正常`)
        } else {
            message.warning("连接测试失败，请检查配置")
        }
    } catch (e) {
        channelStatus.value[channel] = false
        message.error("连接检测出错: " + e.message)
    } finally {
        checkingStatus.value = false
    }
}

const openSettings = async () => {
    try {
        message.loading('加载配置中...')
        const res = await axios.get('/api/settings')
        settingsForm.value = res.data
        showSettingsModal.value = true
        message.destroyAll()
    } catch (e) {
        message.error('加载配置失败')
    }
}

const saveSettings = async () => {
    savingSettings.value = true
    try {
        await axios.post('/api/settings', settingsForm.value)
        message.success('配置已保存 (部分设置可能需要重启生效)')
        showSettingsModal.value = false
    } catch (e) {
        message.error('保存失败: ' + e.message)
    } finally {
        savingSettings.value = false
    }
}

const testNotify = async (channel) => {
    // ... existing ...
    try {
        testingNotify.value = channel
        // quick save
        await axios.post('/api/settings', settingsForm.value)
        const res = await axios.post(`/api/test_notify/${channel}`)
        message.success(res.data.message)
    } catch (e) {
        message.error("测试失败: " + (e.response?.data?.detail || e.message))
    } finally {
        testingNotify.value = null
    }
}

// Change Password State
const passwordForm = ref({
    old_password: '',
    new_password: '',
    confirm_password: ''
})
const changingPassword = ref(false)

const handleChangePassword = async () => {
    if (!passwordForm.value.old_password || !passwordForm.value.new_password) {
        message.warning("请填写完整")
        return
    }
    if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
        message.error("两次新密码输入不一致")
        return
    }
    
    changingPassword.value = true
    try {
        await axios.post('/api/change_password', {
            old_password: passwordForm.value.old_password,
            new_password: passwordForm.value.new_password
        })
        message.success("修改成功，正在通过新密码重新登录...")
        // Wait a bit then redirect
        setTimeout(() => {
            window.location.href = '/login'
        }, 1500)
    } catch (e) {
        message.error("修改失败: " + (e.response?.data?.detail || e.message))
    } finally {
        changingPassword.value = false
    }
}

// Profile State
const showProfileModal = ref(false)
const showPasswordForm = ref(false)
const showEditProfile = ref(false) // Toggle profile edit mode

const profileForm = ref({
    username: '',
    avatar: ''
})
const updatingProfile = ref(false)
const currentUser = ref({ name: 'Administrator', avatar: '', role: '超级管理员' })

// Fetch latest profile info when opening modal
watch(showProfileModal, async (val) => {
    if (val) {
        try {
            const res = await axios.get('/api/check_auth')
            if (res.data.authenticated) {
                currentUser.value.name = res.data.user
                currentUser.value.avatar = res.data.avatar || ''
                // Init form
                profileForm.value.username = res.data.user
                profileForm.value.avatar = res.data.avatar || ''
            }
        } catch (e) {
            console.error("Fetch profile failed", e)
        }
    }
})

const handleUpdateProfile = async () => {
    if (!profileForm.value.username) {
         message.warning("用户名不能为空")
         return
    }
    
    updatingProfile.value = true
    try {
        await axios.post('/api/update_profile', profileForm.value)
        message.success("个人资料已更新")
        
        // Update local view
        currentUser.value.name = profileForm.value.username
        currentUser.value.avatar = profileForm.value.avatar
        showEditProfile.value = false
        
    } catch (e) {
        message.error("更新失败: " + (e.response?.data?.detail || e.message))
    } finally {
        updatingProfile.value = false
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

const handlePlay = async (song) => {
    // 1. Check if we already have a B link in trial_url
    let bvid = null
    if (song.trial_url && song.trial_url.includes('BV')) {
        const match = song.trial_url.match(/(BV\w+)/)
        if (match) bvid = match[1]
    }
    
    // 2. If no BVID, ask backend to match one
    if (!bvid) {
        message.loading(`正在 B 站搜索相关视频...`)
        try {
            const res = await axios.get('/api/match_bilibili', {
                params: { artist: song.author, title: song.title }
            })
            if (res.data.bvid) {
                bvid = res.data.bvid
            }
        } catch (e) {
            console.error(e)
            // Fallback to search page if not found
            window.open(`https://search.bilibili.com/all?keyword=${song.author} ${song.title}`, '_blank')
            return
        }
    }
    
    if (bvid) {
        currentBvid.value = bvid
        showVideoModal.value = true
        message.success('找到了！正在播放')
    } else {
        message.warning('未找到相关视频')
    }
}

// Merged Artists Logic
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

const DEFAULT_AVATAR = 'https://p1.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg'

const getArtistAvatar = (artistName) => {
    const found = mergedArtists.value.find(a => a.name === artistName)
    if (found && found.avatar) return found.avatar.replace('300x300', '800x800')
    return DEFAULT_AVATAR
}


const fetchArtists = async () => {
    try {
        const res = await axios.get('/api/artists')
        rawArtists.value = res.data
    } catch (e) {
        console.error(e)
    }
}

const fetchHistory = async () => {
  loadingHistory.value = true
  try {
    const params = {}
    if (selectedArtistName.value) {
        params.author = selectedArtistName.value
        // If sorting needed, backend handles it
    }
    const res = await axios.get('/api/history', { params })
    history.value = res.data.map(item => ({
      ...item,
      // Format date nicely: "2023.12.25"
      publish_time: new Date(item.publish_time).toLocaleDateString(undefined, { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\//g, '.')
    }))
  } catch (e) {
    console.error(e)
  } finally {
      loadingHistory.value = false
  }
}

const addArtistSmart = async () => {
    if (!newArtistName.value.trim()) return;
    
    adding.value = true
    try {
        const res = await axios.post('/api/artists', { name: newArtistName.value })
        showAddModal.value = false
        newArtistName.value = ''
        await fetchArtists()
        message.success(res.data.message || "已添加")
    } catch (e) {
        message.error("添加失败: " + (e.response?.data?.detail || e.message))
    } finally {
        adding.value = false
    }
}

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

const triggerScan = async () => {
    loading.value = true
    message.loading('开始全局同步...')
    try {
        // Trigger all plugins
        const plugins = ['netease', 'qqmusic', 'bilibili']
        await Promise.all(plugins.map(p => axios.post(`/api/check/${p}`)))
        message.success('全局同步完成')
        fetchHistory()
    } catch (e) {
        message.error('扫描失败')
    } finally {
        loading.value = false
    }
}

const selectArtist = (artist) => {
    if (selectedArtistName.value === artist.name) {
        selectedArtistName.value = null // Toggle off
    } else {
        selectedArtistName.value = artist.name
    }
    fetchHistory()
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
        sysStatus.value = `下次同步: ${min}分钟后`
    } else {
        sysStatus.value = '正在同步中...'
    }
}

// Watch both tab and modal visibility (Moved here to ensure variables are initialized)
watch([activeSettingsTab, showSettingsModal], ([tab, visible]) => {
    if (visible && tab === 'logs') {
        startLogPolling()
    } else {
        stopLogPolling()
    }
})

onMounted(async () => {
  await fetchArtists()
  await fetchHistory()
  await fetchStatus()
  setInterval(updateStatusText, 60000) // Update minute every min
})

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
</script>

<template>
    <div class="app-container">
        <!-- Header -->
        <header class="app-header">
            <div class="header-content">
                <div class="brand-section">
                    <h1>音乐监控助手</h1>
                    <div class="status-badge" v-if="sysStatus">
                        <div class="status-dot"></div>
                        {{ sysStatus }}
                    </div>
                </div>
                <div class="header-actions">
                    <button class="nav-btn" :class="{ spinning: loading }" @click="triggerScan" title="立即同步">
                        <n-icon size="20"><RefreshOutline /></n-icon>
                    </button>
                    <!-- Profile Button -->
                    <button class="nav-btn" @click="showProfileModal = true" title="个人中心">
                        <n-icon size="20"><PersonCircleOutline /></n-icon>
                    </button>
                    <button class="nav-btn" @click="openSettings" title="设置">
                        <n-icon size="20"><SettingsOutline /></n-icon>
                    </button>
                    <button class="nav-btn primary" @click="showAddModal = true" title="添加歌手">
                         <n-icon size="22"><AddOutline /></n-icon>
                    </button>
                </div>
            </div>
        </header>

        <!-- Artist Row (Horizontal Scroll on Mobile, Grid on Desktop) -->
        <section class="artist-section">
            <h2 class="section-title">
                监听列表
                <span class="count">{{ mergedArtists.length }}</span>
            </h2>
            <div class="artist-grid-wrapper">
                 <div v-for="artist in mergedArtists" :key="artist.name" 
                      class="artist-item" 
                      :class="{ active: selectedArtistName === artist.name }"
                      @click="selectArtist(artist)">
                      
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
                                  <button class="mini-btn update" @click.stop="triggerCheck(artist)" title="更新">
                                      <n-icon><RefreshOutline /></n-icon>
                                  </button>
                                  <button class="mini-btn delete" @click.stop="deleteMergedArtist(artist)" title="删除">
                                      <n-icon><TrashOutline /></n-icon>
                                  </button>
                              </div>
                          </div>
                      </div>
                      
                      <div class="artist-name">{{ artist.name }}</div>
                 </div>
                 
                 <!-- Add Item (Quick Access) -->
                 <div class="artist-item add-item" @click="showAddModal = true">
                     <div class="avatar-container add-placeholder-img">
                        <img :src="DEFAULT_AVATAR" class="artist-avatar" />
                        <div class="add-icon-overlay">
                             <n-icon size="32"><AddOutline /></n-icon>
                        </div>
                     </div>
                     <div class="artist-name">添加</div>
                 </div>
            </div>
        </section>

        <!-- Feed Section -->
        <section class="feed-section">
            <h2 class="section-title">
                {{ selectedArtistName ? selectedArtistName : '最新动态' }}
                <n-button v-if="selectedArtistName" text size="tiny" class="clear-filter-btn" @click="selectArtist({name: selectedArtistName})">
                    <template #icon><n-icon><CloseOutline /></n-icon></template>
                    显示全部
                </n-button>
            </h2>
            
            <div v-if="loadingHistory" class="skeleton-table">
                 <div v-for="i in 5" :key="i" class="table-row skeleton-row">
                     <div class="col-cover skeleton"></div>
                     <div class="col-track skeleton" style="width: 40%; height: 20px;"></div>
                     <div class="col-artist skeleton" style="width: 20%; height: 20px; margin-left: auto;"></div>
                 </div>
            </div>

            <div class="song-table" v-else-if="history.length > 0">
                    <div class="table-header">
                        <div class="col-cover"></div>
                        <div class="col-track">歌曲</div>
                        <div class="col-artist">歌手</div>
                        <div class="col-album">专辑</div>
                        <div class="col-time">发布时间</div>
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
                                 <span v-if="song.source === 'bilibili'" class="platform-dot bili" title="Bilibili"></span>
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
                    <n-empty description="暂无最新动态，好消息是也没错过什么" size="large" />
                </div>
        </section>

        <!-- Add Modal (Spotlight Style) -->
        <n-modal v-model:show="showAddModal" class="spotlight-modal" :mask-closable="true">
            <div class="spotlight-content">
                <div class="spotlight-icon">
                    <n-icon><SearchOutline /></n-icon>
                </div>
                <input 
                    v-model="newArtistName" 
                    class="spotlight-input" 
                    placeholder="搜索并添加歌手 (如: 陈奕迅)..."  
                    @keyup.enter="addArtistSmart"
                    v-autofocus
                />
                <div class="spotlight-loader" v-if="adding">
                    <n-spin size="small" />
                </div>
            </div>
        </n-modal>
        <n-modal v-model:show="showSettingsModal" class="settings-modal-ios" :mask-closable="true">
            <div class="ios-settings-container">
                <!-- Header -->
                <div class="ios-header">
                    <div class="ios-title">系统设置</div>
                    <div class="ios-close-btn" @click="showSettingsModal = false">
                        <n-icon size="20"><CloseOutline /></n-icon>
                    </div>
                </div>

                <!-- Content -->
                <div class="ios-content">
                    <n-tabs v-model:value="activeSettingsTab" type="segment" animated class="ios-tabs">
                        <!-- Tab 1: Monitor Services -->
                        <n-tab-pane name="monitor" tab="监听源">
                            <div class="ios-group-title">数据源开关与频率</div>
                            <div class="ios-group">
                                <div class="ios-item" v-for="(cfg, key) in settingsForm.monitor" :key="key">
                                    <div class="ios-row-main">
                                        <div class="ios-label">
                                            {{ getServiceName(key) }}
                                            <span class="ios-badge" :class="{ active: cfg.enabled }">
                                                {{ cfg.enabled ? '运行中' : '已暂停' }}
                                            </span>
                                        </div>
                                        <n-switch v-model:value="cfg.enabled" class="ios-switch" />
                                    </div>
                                    <div class="ios-row-sub" v-if="cfg.enabled">
                                        <span>检查间隔</span>
                                        <div class="ios-input-wrapper">
                                            <n-input-number v-model:value="cfg.interval" size="small" :show-button="false" class="ios-number-input" />
                                            <span class="unit">分钟</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </n-tab-pane>

                        <!-- Tab 2: Notifications -->
                        <n-tab-pane name="notify" tab="推送通道">
                            <!-- Channel Selector -->
                            <div class="ios-segmented-control">
                                <div 
                                    class="segment-item" 
                                    :class="{ active: activeNotifyChannel === 'wecom' }"
                                    @click="activeNotifyChannel = 'wecom'"
                                >
                                    企业微信
                                </div>
                                <div 
                                    class="segment-item" 
                                    :class="{ active: activeNotifyChannel === 'telegram' }"
                                    @click="activeNotifyChannel = 'telegram'"
                                >
                                    Telegram
                                </div>
                            </div>
                            
                            <!-- Dynamic Channel Settings -->
                            <div class="ios-group-title">
                                {{ activeNotifyChannel === 'wecom' ? '企业微信设置' : 'Telegram 设置' }}
                            </div>
                            
                            <div class="ios-group">
                                <!-- Switch Row -->
                                <div class="ios-item">
                                    <div class="ios-row-main">
                                        <div class="ios-label">
                                            启用推送
                                        </div>
                                        <n-switch v-model:value="channelConfig.enabled" class="ios-switch" />
                                    </div>
                                </div>

                                <!-- Status Row (Only if enabled) -->
                                <div class="ios-item" v-if="channelConfig.enabled">
                                    <div class="ios-row-main" style="justify-content: flex-start; gap: 12px;">
                                        <div class="status-dot" :class="{ 
                                            online: channelStatus[activeNotifyChannel] === true,
                                            offline: channelStatus[activeNotifyChannel] === false 
                                        }"></div>
                                        <div class="status-text">
                                            {{ channelStatus[activeNotifyChannel] === true ? 'API 联通正常' : (channelStatus[activeNotifyChannel] === false ? '连接失败' : '未检测状态') }}
                                        </div>
                                        <div style="flex: 1"></div>
                                        <n-button 
                                            size="tiny" round secondary
                                            @click="checkChannelStatus(activeNotifyChannel)" 
                                            :loading="checkingStatus">
                                            检测联通性
                                        </n-button>
                                        <n-button 
                                            size="tiny" round ghost type="primary"
                                            @click="testNotify(activeNotifyChannel)" 
                                            :loading="testingNotify === activeNotifyChannel">
                                            发送测试消息
                                        </n-button>
                                    </div>
                                </div>

                                <!-- WeCom Forms -->
                                <div class="ios-item" v-if="activeNotifyChannel === 'wecom' && channelConfig.enabled">
                                     <div class="ios-form-stack">
                                        <div class="stack-row">
                                            <span class="label">Corp ID</span>
                                            <input v-model="settingsForm.notify.wecom.corp_id" class="ios-text-input" placeholder="ww..." />
                                        </div>
                                        <div class="stack-row">
                                            <span class="label">Secret</span>
                                            <input type="password" v-model="settingsForm.notify.wecom.secret" class="ios-text-input" placeholder="•••••" />
                                        </div>
                                    <div class="stack-row">
                                            <span class="label">Agent ID</span>
                                            <input v-model="settingsForm.notify.wecom.agent_id" class="ios-text-input" placeholder="1000002" />
                                        </div>
                                        <div class="stack-row">
                                            <span class="label">Token</span>
                                            <input v-model="settingsForm.notify.wecom.token" class="ios-text-input" placeholder="用于回调验证" />
                                        </div>
                                        <div class="stack-row">
                                            <span class="label">AES Key</span>
                                            <input v-model="settingsForm.notify.wecom.aes_key" class="ios-text-input" placeholder="EncodingAESKey" />
                                        </div>
                                    </div>
                                    <div class="ios-row-sub" style="margin-top: 10px; font-size: 13px; color: #86868b; padding-left: 16px;">
                                        应用回调 URL: http://你的公网IP:8000/api/wecom/callback
                                    </div>
                                </div>

                                <!-- Telegram Forms -->
                                <div class="ios-item" v-if="activeNotifyChannel === 'telegram' && channelConfig.enabled">
                                     <div class="ios-form-stack">
                                        <div class="stack-row">
                                            <span class="label">Bot Token</span>
                                            <input type="password" v-model="settingsForm.notify.telegram.bot_token" class="ios-text-input" placeholder="123456:ABC..." />
                                        </div>
                                        <div class="stack-row">
                                            <span class="label">Chat ID</span>
                                            <input v-model="settingsForm.notify.telegram.chat_id" class="ios-text-input" placeholder="-100..." />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </n-tab-pane>

                        <!-- Tab 3: System Logs -->
                        <n-tab-pane name="logs" tab="系统日志">
                            <div class="ios-group-title">
                                运行日志
                                <n-button size="tiny" text @click="fetchLogs" :loading="refreshingLogs" style="margin-left: 8px">
                                    <template #icon><n-icon><RefreshOutline /></n-icon></template>
                                    刷新
                                </n-button>
                            </div>
                            <div class="ios-group" style="background: #1e1e1e; color: #fff;">
                                <div class="log-console" ref="logContainer">
                                    <div v-if="logs.length === 0" class="log-empty">暂无日志</div>
                                    <div v-else v-for="(log, i) in logs" :key="i" class="log-line">
                                        <span class="log-time">[{{ log.time }}]</span>
                                        <span class="log-level" :class="log.level.toLowerCase()">{{ log.level }}</span>
                                        <span class="log-source">{{ log.source }}:</span>
                                        <span class="log-msg">{{ log.message }}</span>
                                    </div>
                                </div>
                            </div>
                        </n-tab-pane>

                        <!-- Tab 4: System (Orig Tab 3) -->
                        <n-tab-pane name="system" tab="高级设置">
                            <div class="ios-group-title">全局参数</div>
                            <div class="ios-group">
                                <div class="ios-item">
                                    <div class="ios-row-main">
                                        <div class="ios-label">默认检查间隔</div>
                                        <div class="ios-input-wrapper">
                                            <n-input-number v-model:value="settingsForm.global.check_interval_minutes" size="small" :show-button="false" class="ios-number-input" />
                                            <span class="unit">分钟</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="ios-item">
                                    <div class="ios-row-main">
                                        <div class="ios-label">日志级别</div>
                                        <n-select v-model:value="settingsForm.global.log_level" :options="logOptions" size="small" style="width: 100px" />
                                    </div>
                                </div>
                            </div>
                        </n-tab-pane>
                    </n-tabs>
                </div>

                <!-- Footer Action -->
                <div class="ios-footer">
                    <n-button type="primary" block round size="large" @click="saveSettings" :loading="savingSettings" class="ios-save-btn">
                        保存更改
                    </n-button>
                </div>
            </div>
        </n-modal>
        
        <!-- Profile Modal -->
        <n-modal v-model:show="showProfileModal" class="settings-modal-ios profile-modal" :mask-closable="true">
            <div class="ios-settings-container profile-container">
                <!-- Header -->
                <div class="ios-header">
                    <div class="ios-title">个人中心</div>
                    <div class="ios-close-btn" @click="showProfileModal = false">
                        <n-icon size="20"><CloseOutline /></n-icon>
                    </div>
                </div>

                <!-- Content -->
                <div class="ios-content">
                    <!-- User Card -->
                    <div class="profile-card">
                        <div class="profile-avatar">
                            <img v-if="currentUser.avatar" :src="currentUser.avatar" class="avatar-img" />
                            <n-icon v-else size="40"><PersonCircleOutline /></n-icon>
                        </div>
                        <div class="profile-info">
                            <div class="profile-name">{{ currentUser.name }}</div>
                            <div class="profile-role">{{ currentUser.role }}</div>
                        </div>
                        <div class="profile-action">
                             <n-button size="small" round secondary @click="showEditProfile = !showEditProfile">
                                 {{ showEditProfile ? '取消' : '编辑' }}
                             </n-button>
                        </div>
                    </div>

                    <!-- Edit Profile Form -->
                    <div v-if="showEditProfile" class="ios-group-title">编辑资料</div>
                    <div v-if="showEditProfile" class="ios-group">
                         <div class="ios-item" style="background: transparent; padding: 0;">
                             <div class="ios-form-stack" style="margin: 0; border-top: none;">
                                <div class="stack-row">
                                    <span class="label">用户名</span>
                                    <input type="text" v-model="profileForm.username" class="ios-text-input" placeholder="输入新的用户名" />
                                </div>
                                <div class="stack-row">
                                    <span class="label">头像URL</span>
                                    <input type="text" v-model="profileForm.avatar" class="ios-text-input" placeholder="输入头像图片链接" />
                                </div>
                             </div>
                             <div style="padding: 12px 16px;">
                                 <n-button type="primary" block round @click="handleUpdateProfile" :loading="updatingProfile">
                                     保存更新
                                 </n-button>
                             </div>
                        </div>
                    </div>

                    <div class="ios-group-title">账户管理</div>
                    <div class="ios-group">
                        <!-- Change Password Toggle -->
                        <div class="ios-item cursor-pointer" @click="showPasswordForm = !showPasswordForm">
                            <div class="ios-row-main">
                                <div class="ios-label">修改密码</div>
                                <div class="ios-arrow" :class="{ rotated: showPasswordForm }">›</div>
                            </div>
                        </div>

                        <!-- Password Form (Collapsible) -->
                         <div v-if="showPasswordForm" class="ios-item" style="background: transparent; padding: 0;">
                             <div class="ios-form-stack" style="margin: 0; border-top: none;">
                                <div class="stack-row">
                                    <span class="label">当前密码</span>
                                    <input type="password" v-model="passwordForm.old_password" class="ios-text-input" placeholder="输入旧密码" />
                                </div>
                                <div class="stack-row">
                                    <span class="label">新密码</span>
                                    <input type="password" v-model="passwordForm.new_password" class="ios-text-input" placeholder="输入新密码" />
                                </div>
                                <div class="stack-row">
                                    <span class="label">确认密码</span>
                                    <input type="password" v-model="passwordForm.confirm_password" class="ios-text-input" placeholder="再次输入新密码" />
                                </div>
                             </div>
                             <div style="padding: 12px 16px;">
                                 <n-button type="warning" block round @click="handleChangePassword" :loading="changingPassword">
                                     确认修改
                                 </n-button>
                             </div>
                        </div>
                    </div>

                    <div class="ios-group">
                        <div class="ios-item cursor-pointer" @click="handleLogout">
                            <div class="ios-row-main" style="color: #FF3B30;">
                                <div class="ios-label" style="color: #FF3B30;">
                                    <n-icon style="margin-right:8px"><LogOutOutline /></n-icon>
                                    退出登录
                                </div>
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </n-modal>

        <!-- Video Player Modal -->
        <n-modal v-model:show="showVideoModal" class="video-modal" :mask-closable="true">
            <div class="video-content">
                <iframe 
                    v-if="currentBvid"
                    :src="`//player.bilibili.com/player.html?bvid=${currentBvid}&page=1&high_quality=1&danmaku=0`" 
                    allowfullscreen="allowfullscreen" 
                    width="100%" 
                    height="100%" 
                    scrolling="no" 
                    frameborder="0" 
                    sandbox="allow-top-navigation allow-same-origin allow-forms allow-scripts">
                </iframe>
            </div>
        </n-modal>
    </div>
</template>

<style scoped>
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
    font-weight: 800; /* Bolder */
    color: #1d1d1f; /* Apple dark gray */
    letter-spacing: -0.025em; /* Tighter tracking */
    margin-right: 16px;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif;
}
.brand-section {
    display: flex;
    align-items: center;
}
.status-badge {
    display: flex;
    align-items: center;
    font-size: 13px;
    color: var(--text-secondary);
    background: rgba(0,0,0,0.03);
    padding: 6px 12px;
    border-radius: 99px;
    gap: 6px;
}
.status-dot {
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
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    background-color: rgba(0,0,0,0.04); /* Ultra light gray */
    color: #1d1d1f;
    backdrop-filter: blur(10px);
}
.nav-btn:hover {
    background-color: #e0e0e0;
    transform: scale(1.05);
}
.nav-btn.primary {
    background-color: #FA2D48; /* Apple Music Red */
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

/* Sections */
.section-title {
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 8px;
}
/* Settings Modal */
.setting-item {
    background: #f9f9f9;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 12px;
    border: 1px solid #eee;
}
.setting-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}
.setting-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    display: flex;
    align-items: center;
}
.sub-form {
    padding-top: 12px;
    border-top: 1px solid #eee;
}

/* Video Modal */
.video-modal {
    width: 85vw !important;
    max-width: 1400px;
    background: #000;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 32px 64px rgba(0,0,0,0.6);
}
.video-content {
    width: 100%;
    /* Force 16:9 Aspect Ratio based on width */
    height: calc(85vw * 9 / 16);
    max-height: calc(1400px * 9 / 16);
    position: relative;
}
iframe {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
}

/* Artist Grid (Minimalist) */
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
    background: #fff;
    box-shadow: var(--shadow-sm);
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
.platform-dot.bili { background-color: #00A1D6; } /* Official Bili Blue */

.col-artist, .col-album {
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px;
}
.col-time { font-size: 13px; }

.action-link {
    font-size: 13px;
    color: var(--accent-primary);
    font-weight: 500;
}

/* Spotlight Modal */
.spotlight-modal {
    background: transparent;
    box-shadow: none;
}
.spotlight-content {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(20px);
    border-radius: 16px;
    padding: 20px;
    box-shadow: var(--shadow-float);
    display: flex;
    align-items: center;
    gap: 16px;
    width: 600px;
    max-width: 90vw;
    border: 1px solid rgba(0,0,0,0.05);
}

.spotlight-icon {
    font-size: 24px;
    color: var(--text-secondary);
}

.spotlight-input {
    flex: 1;
    border: none;
    background: transparent;
    font-size: 22px;
    outline: none;
    color: var(--text-primary);
}
.spotlight-input::placeholder {
    color: var(--text-tertiary);
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

/* iOS Settings Modal */
:deep(.settings-modal-ios) {
    background: transparent !important;
}
:deep(.settings-modal-ios .n-modal-mask) {
    background-color: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(20px);
}

.ios-settings-container {
    width: 640px;
    max-width: 90vw;
    background: rgba(255, 255, 255, 0.82); /* Lighter, translucency */
    backdrop-filter: blur(50px) saturate(180%);
    border-radius: 16px; /* Smooth corners */
    box-shadow: 0 40px 100px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,0,0,0.05); /* Softer deep shadow */
    overflow: hidden;
    position: relative;
    /* Font */
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif;
    color: #1d1d1f;
}

/* Header */
.ios-header {
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05); /* Faint separator */
    background: rgba(255,255,255,0.0); /* Transparent header */
}
.ios-title {
    font-size: 17px;
    font-weight: 600;
    color: #1d1d1f;
}
.ios-close-btn {
    position: absolute;
    right: 12px;
    width: 28px;
    height: 28px;
    background: rgba(118, 118, 128, 0.12);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.2s;
    color: #8E8E93;
}
.ios-close-btn:hover {
    background: rgba(118, 118, 128, 0.24);
    color: #1C1C1E;
}

/* Content */
.ios-content {
    padding: 20px;
    max-height: 70vh;
    overflow-y: auto;
}

/* Grouped List */
.ios-group-title {
    font-size: 20px; /* Larger, bolder headers */
    text-transform: none; /* Normal case */
    color: #1d1d1f;
    margin: 32px 0 16px 4px;
    font-weight: 700;
    letter-spacing: -0.015em;
}
.ios-group-title:first-child { margin-top: 0; }

.ios-group {
    background: transparent; /* Remove container BG */
    border-radius: 0;
    overflow: visible;
    margin-bottom: 16px;
}
.ios-item {
    padding: 0 16px;
}
/* Separator logic: add border-bottom to all except last */
.ios-item:not(:last-child):after {
    content: '';
    display: block;
    height: 1px;
    background: rgba(60, 60, 67, 0.1);
    margin-left: 0; /* Full width inside item? No, usually inset. */
}
.ios-item {
    position: relative;
    background: rgba(255, 255, 255, 0.6); /* Individual item translucency */
    border-radius: 12px;
    margin-bottom: 10px;
    padding: 0 16px;
    transition: background 0.2s;
}
.ios-item:hover {
    background: rgba(255, 255, 255, 0.8);
}
.ios-item:after { display: none !important; } /* Remove separators */

.ios-row-main {
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.ios-label {
    font-size: 17px;
    color: #000;
    display: flex;
    align-items: center;
    gap: 8px;
}
.ios-badge {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 6px;
    background: #F2F2F7;
    color: #8E8E93;
}
.ios-badge.active {
    background: #34C759;
    color: #fff;
}

.ios-row-sub {
    padding: 0 0 12px 0;
    font-size: 14px;
    color: #86868b;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Input Stack (Nested Form) */
.ios-form-stack {
    background: #F2F2F7;
    padding: 10px 16px;
    margin: 0 -16px; /* Bleed to edge of item */
    border-top: 1px solid rgba(60, 60, 67, 0.1);
}

/* Number Input Wrapper */
.ios-input-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;
}
.ios-number-input {
    width: 80px;
    text-align: center;
}
:deep(.ios-number-input .n-input) {
    background-color: rgba(0,0,0,0.05); /* Slight BG for visibility */
    border-radius: 6px;
}
:deep(.ios-number-input .n-input__input-el) {
    text-align: center;
}
.unit {
    color: #8E8E93;
    font-size: 15px;
}
.stack-row {
    display: flex;
    align-items: center;
    height: 44px;
    border-bottom: 1px solid rgba(60, 60, 67, 0.1);
}
.stack-row:last-child { border-bottom: none; }
.stack-row .label {
    width: 100px;
    font-size: 15px;
    color: #000;
}
.ios-text-input {
    flex: 1;
    border: none;
    background: rgba(0,0,0,0.05); /* Slight BG to look editable */
    border-radius: 6px;
    font-size: 15px;
    color: #000;
    outline: none;
    text-align: left; /* Left align for easier editing */
    padding: 4px 8px;
    margin-right: 8px;
    transition: background 0.2s;
}
.ios-text-input:focus {
    background: rgba(0,0,0,0.08);
}
.ios-text-input::placeholder { color: #C7C7CC; }

/* Custom Switch Override if needed (Naive UI switch is okay, but let's tweak) */
.ios-switch { transform: scale(0.9); }

/* Tabs Override */
:deep(.ios-tabs .n-tabs-nav) {
    background: transparent !important;
    padding: 0 10px 10px;
}
/* Footer */
.ios-footer {
    padding: 20px 24px;
    background: rgba(255,255,255,0.3);
    border-top: 1px solid rgba(0, 0, 0, 0.05);
}
.ios-save-btn {
    font-weight: 600;
    font-size: 17px;
    height: 48px; border-radius: 12px; /* Bigger button */
    box-shadow: 0 4px 12px rgba(250, 45, 72, 0.25);
}

/* Segmented Control */
.ios-segmented-control {
    background: rgba(118, 118, 128, 0.12);
    border-radius: 9px;
    padding: 2px;
    display: flex;
    margin: 16px 16px 0 16px;
}
.segment-item {
    flex: 1;
    text-align: center;
    padding: 6px 0;
    font-size: 13px;
    font-weight: 500;
    color: #000;
    border-radius: 7px;
    cursor: pointer;
    transition: all 0.2s;
}
.segment-item.active {
    background: #fff;
    box-shadow: 0 3px 8px rgba(0,0,0,0.12), 0 3px 1px rgba(0,0,0,0.04);
}

/* Status Indicator */
.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #E5E5EA; /* Gray for unknown */
}
.status-dot.online { background: #34C759; box-shadow: 0 0 6px rgba(52, 199, 89, 0.4); }
.status-dot.offline { background: #FF3B30; }

.status-text {
    font-size: 13px;
    color: #8E8E93;
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

.table-row:hover .cover-wrapper {
     transform: scale(1.05) translateZ(0); /* Subtle pop for album art */
}

/* Log Console */
.log-console {
    height: 300px;
    background: #1e1e1e;
    overflow-y: auto;
    padding: 12px;
    font-family: Consolas, Monaco, "Courier New", monospace;
    font-size: 12px;
    line-height: 1.5;
}
.log-line {
    word-break: break-all;
    margin-bottom: 2px;
}
.log-time { color: #666; margin-right: 8px; }
.log-source { color: #569cd6; margin-right: 6px; }
.log-msg { color: #d4d4d4; }

.log-level.info { color: #4ec9b0; margin-right: 6px; }
.log-level.warning { color: #cca700; margin-right: 6px; }
.log-level.error { color: #f44336; margin-right: 6px; }
.log-level.debug { color: #808080; margin-right: 6px; }

.log-empty { color: #555; text-align: center; margin-top: 100px; }

/* Profile Styles */
.profile-card {
    display: flex;
    align-items: center;
    padding: 24px;
    background: rgba(255, 255, 255, 0.5);
    border-radius: 16px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}
.profile-avatar {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: #f2f2f7;
    color: #8E8E93;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 16px;
    overflow: hidden; /* Ensure image fits */
}
.avatar-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.profile-info {
    flex: 1;
}
.profile-name {
    font-size: 20px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 4px;
}
.profile-role {
    font-size: 14px;
    color: #86868b;
}

.cursor-pointer { cursor: pointer; }

.ios-arrow {
    font-size: 20px;
    color: #C7C7CC;
    transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.ios-arrow.rotated {
    transform: rotate(90deg);
}

.profile-container {
    height: auto; /* Fit content */
    max-height: 80vh;
}
</style>
