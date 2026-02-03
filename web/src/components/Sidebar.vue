<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  HomeOutline, 
  SearchOutline, 
  LibraryOutline, 
  TimeOutline, 
  SettingsOutline,
  PersonOutline
} from '@vicons/ionicons5'
import { NIcon } from 'naive-ui'

const router = useRouter()
const route = useRoute()

const menuItems = [
  { key: 'listen-now', label: '现在就听', icon: HomeOutline, path: '/' },
  { key: 'search', label: '搜索', icon: SearchOutline, path: '/search' },
  { key: 'library', label: '资料库', icon: LibraryOutline, path: '/library' },
  { key: 'history', label: '最近播放', icon: TimeOutline, path: '/history' },
]

const bottomItems = [
  { key: 'settings', label: '设置', icon: SettingsOutline, path: '/settings' },
  { key: 'profile', label: '个人中心', icon: PersonOutline, path: '/profile' },
]

const isActive = (path: string) => route.path === path
</script>

<template>
  <aside class="sidebar apple-transition">
    <div class="sidebar-header">
      <div class="app-logo">
        <div class="logo-inner"></div>
        <span>Music Monitor</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div 
        v-for="item in menuItems" 
        :key="item.key"
        class="nav-item clickable"
        :class="{ active: isActive(item.path) }"
        @click="router.push(item.path)"
      >
        <n-icon :component="item.icon" size="20" />
        <span>{{ item.label }}</span>
      </div>
      
      <div class="nav-divider"></div>
      
      <div 
        v-for="item in bottomItems" 
        :key="item.key"
        class="nav-item clickable"
        :class="{ active: isActive(item.path) }"
        @click="router.push(item.path)"
      >
        <n-icon :component="item.icon" size="20" />
        <span>{{ item.label }}</span>
      </div>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  padding: 24px 12px;
  /* position and z-index handled by style.css .sidebar-area */
}

.sidebar-header {
  padding: 0 12px 24px;
}

.app-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 18px;
  color: #FFFFFF;
}

.logo-inner {
  width: 24px;
  height: 24px;
  background-color: var(--sp-green);
  border-radius: 50%;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 20px; /* Increased gap for better clarity */
  padding: 10px 16px; /* Slightly tighter vertical padding */
  border-radius: 4px;
  color: var(--text-secondary);
  font-weight: 700; /* Bold sidebar text */
  font-size: 14px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.nav-item:hover {
  color: #FFFFFF;
}

.nav-item.active {
  color: #FFFFFF;
  background-color: transparent;
}

.nav-item.active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px; /* Precise alignment */
  bottom: 8px;
  width: 3px; /* Slightly thinner, more elegant */
  background-color: var(--sp-green);
  border-radius: 4px;
}

.nav-divider {
  height: 1px;
  background-color: #282828;
  margin: 12px 16px;
}
</style>
