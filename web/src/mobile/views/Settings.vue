<template>
  <div class="sp-settings">
    <div class="sp-gradient-bg"></div>

    <header class="sp-header">
      <h1 class="text-title">设置</h1>
    </header>

    <main class="sp-settings-content">
      <!-- 账户信息 -->
      <section class="sp-settings-group">
        <div class="user-card">
           <div class="user-avatar-box">
              <n-icon size="24" :component="PersonOutline" />
           </div>
           <div class="user-info">
              <div class="username">{{ userStore.username }}</div>
              <div class="user-status">在线</div>
           </div>
           <button class="sp-btn-small" @click="handleLogout">退出</button>
        </div>
      </section>

      <!-- 偏好设置 -->
      <h3 class="group-title">偏好设置</h3>
      <section class="sp-settings-group">
        <div class="sp-list-item">
          <div class="item-icon"><n-icon :component="MoonOutline" /></div>
          <div class="item-content">深色模式</div>
          <div class="item-action">
            <n-switch :value="settingsStore.isDark" @update:value="settingsStore.toggleTheme" />
          </div>
        </div>
        <div class="sp-list-item">
          <div class="item-icon"><n-icon :component="GlobeOutline" /></div>
          <div class="item-content">语言</div>
          <div class="item-value">简体中文</div>
        </div>
      </section>

      <!-- 通知与同步 -->
      <h3 class="group-title">通知与同步</h3>
      <section class="sp-settings-group">
        <div class="sp-list-item clickable" @click="handleTestNotify">
          <div class="item-icon"><n-icon :component="NotificationsOutline" /></div>
          <div class="item-content">测试通知推送</div>
          <n-icon class="chevron" :component="ChevronForwardOutline" />
        </div>
        <div class="sp-list-item clickable" @click="onRefresh">
          <div class="item-icon"><n-icon :component="SyncOutline" /></div>
          <div class="item-content">同步云端资料库</div>
          <n-icon class="chevron" :component="ChevronForwardOutline" />
        </div>
      </section>

      <!-- 底部信息 -->
      <div class="sp-settings-footer">
        <p>Music Monitor</p>
        <p class="version">v{{ versionInfo }} · Spotify Edition</p>
      </div>
    </main>

    <!-- Spotify Mobile TabBar -->
    <nav class="sp-tabbar">
      <div 
        v-for="tab in tabs" 
        :key="tab.name"
        class="tab-item clickable"
        :class="{ 'is-active': activeTab === tab.name }"
        @click="onTabChange(tab.name)"
      >
        <n-icon size="26" :component="getTabIcon(tab.icon, activeTab === tab.name)" />
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon, NSwitch } from 'naive-ui'
import { 
    PersonOutline, MoonOutline, GlobeOutline, NotificationsOutline, 
    SyncOutline, ChevronForwardOutline,
    Home, HomeOutline, Search, SearchOutline, Library, LibraryOutline
} from '@vicons/ionicons5'
import { useSettingsStore, useUserStore, useLibraryStore } from '@/stores'
import axios from 'axios'

const router = useRouter()
const route = useRoute()
const settingsStore = useSettingsStore()
const userStore = useUserStore()
const libraryStore = useLibraryStore()

// Active tab detection
const activeTab = ref('')
const versionInfo = ref('Loading...')

const handleLogout = async () => {
    await userStore.logout()
    router.replace({ name: 'Login' })
}

const handleTestNotify = async () => {
  try {
    await settingsStore.triggerCheck('wecom')
    alert('测试通知已发送')
  } catch {
    alert('发送失败')
  }
}

const onRefresh = async () => {
  await libraryStore.fetchSongs(1)
  alert('资料库同步完成')
}

// Fetch Version
const fetchVersion = async () => {
  try {
    const res = await axios.get('/api/version')
    if (res.data && res.data.version) {
       versionInfo.value = res.data.version
    }
  } catch (e) {
    console.error('Failed to fetch version', e)
    versionInfo.value = 'Unknown'
  }
}

// 统一的 Tab 定义，移除 Settings Tab (因为通常它是独立的或者是 Profile)
// 但为了保持一致性，如果这里展示 TabBar，应该允许切回主页
const tabs = [
  { name: 'home', icon: 'home', label: '首页' },
  { name: 'search', icon: 'search', label: '搜索' },
  { name: 'library', icon: 'library', label: '资料库' }
]

const getTabIcon = (type: string, active: boolean) => {
    if (type === 'home') return active ? Home : HomeOutline
    if (type === 'search') return active ? Search : SearchOutline
    return active ? Library : LibraryOutline
}

const onTabChange = (name: string) => {
    activeTab.value = name
    const routes: Record<string, string> = { 
        home: 'MobileHome', library: 'MobileLibrary', 
        search: 'MobileSearch'
    }
    router.push({ name: routes[name] })
}

onMounted(() => {
  settingsStore.fetchSettings()
  fetchVersion()
})
</script>

<style scoped>
.sp-settings {
  min-height: 100vh;
  background: #121212;
  color: #fff;
  padding-bottom: 120px;
  position: relative;
}

.sp-gradient-bg {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 200px;
  background: linear-gradient(to bottom, rgba(50,50,50, 0.3), transparent);
  pointer-events: none;
}

.sp-header {
  padding: 16px;
  padding-top: max(24px, env(safe-area-inset-top));
  margin-bottom: 24px;
}
.text-title { font-size: 24px; font-weight: 700; }

.sp-settings-content {
  padding: 0 16px;
  position: relative;
  z-index: 1;
}

.group-title {
  font-size: 13px;
  font-weight: 700;
  color: #b3b3b3;
  margin: 24px 0 8px 4px;
  text-transform: uppercase;
}

.sp-settings-group {
  background: #282828;
  border-radius: 8px;
  overflow: hidden;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
}
.user-avatar-box {
  width: 48px; height: 48px;
  border-radius: 50%;
  background: #555;
  display: flex; align-items: center; justify-content: center;
}
.user-info { flex: 1; }
.username { font-size: 16px; font-weight: 700; color: #fff; }
.user-status { font-size: 12px; color: var(--sp-green); }

.sp-btn-small {
  padding: 6px 16px;
  border-radius: 16px;
  background: transparent;
  border: 1px solid #777;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.sp-list-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.sp-list-item:last-child { border-bottom: none; }
.sp-list-item:active { background: #333; }

.item-icon { color: #b3b3b3; font-size: 20px; display: flex; }
.item-content { flex: 1; font-size: 15px; font-weight: 500; }
.item-value { color: #b3b3b3; font-size: 13px; margin-right: 8px; }
.chevron { color: #777; font-size: 16px; }

.sp-settings-footer {
  text-align: center;
  margin-top: 48px;
  color: #777;
  font-size: 12px;
}
.version { margin-top: 4px; }

/* TabBar */
.sp-tabbar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 80px; 
  background: linear-gradient(to top, #000 0%, rgba(0,0,0,0.95) 100%);
  display: flex;
  justify-content: space-around;
  padding-top: 12px;
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 100;
}
.tab-item { display: flex; flex-direction: column; align-items: center; gap: 4px; color: #b3b3b3; width: 60px; }
.tab-item.is-active { color: #fff; }
.tab-label { font-size: 10px; font-weight: 500; }
</style>
