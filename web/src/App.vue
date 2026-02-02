<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="themeOverrides">
    <n-global-style />
    <n-message-provider>
      <!-- Expose Message API -->
      <MessageProxy />
      
      <n-dialog-provider>
          <div class="app-layout" :class="{ 'no-layout': hideLayout }">
            <Sidebar v-if="!hideLayout" class="sidebar-area" />
            
            <main class="main-content-area">
              <router-view />
            </main>

            <BottomPlayer v-if="!hideLayout" class="player-area" />
            <LyricsPanel v-if="!hideLayout" />
          </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
/**
 * 应用根组件 - Spotify 风格重构版
 */
import { onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { NConfigProvider, NGlobalStyle, NMessageProvider, NDialogProvider, darkTheme } from 'naive-ui'
import { useSettingsStore } from '@/stores'
import { useWebSocketStore } from '@/stores/websocket'
import Sidebar from '@/components/Sidebar.vue'
import BottomPlayer from '@/components/BottomPlayer.vue'
import LyricsPanel from '@/components/LyricsPanel.vue'
import MessageProxy from '@/components/MessageProxy.vue'

const route = useRoute()
const settingsStore = useSettingsStore()
const wsStore = useWebSocketStore()

const hideLayout = computed(() => route.name === 'Login')

// Spotify Style 主题配置
const themeOverrides = computed(() => ({
    common: {
        primaryColor: '#1DB954',
        primaryColorHover: '#1ED760',
        primaryColorPressed: '#1AA34A',
        borderRadius: '8px',
        baseColor: '#121212'
    },
    Card: {
        color: '#181818',
        borderColor: 'transparent',
        borderRadius: '8px'
    },
    Input: {
        color: '#282828',
        colorFocus: '#333333',
        borderRadius: '4px'
    }
}))

onMounted(() => {
  settingsStore.initTheme()
  wsStore.connect()
})
</script>

<style>
/* 核心布局由 style.css 控制，此处处理微调 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
