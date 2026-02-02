<script setup lang="ts">
/**
 * 桌面端设置视图 - 侧边栏布局 (优化版)
 */
import { onMounted, ref } from 'vue'
import { NSpin, NIcon } from 'naive-ui'
import { useSettingsStore } from '@/stores'
import { 
    SettingsOutline, NotificationsOutline 
} from '@vicons/ionicons5'

// 设置子组件
import GeneralSettings from '@/components/settings/GeneralSettings.vue'
import NotifySettings from '@/components/settings/NotifySettings.vue'

const settingsStore = useSettingsStore()
const activeTab = ref('general')

const tabs = [
    { key: 'general', label: '通用设置', icon: SettingsOutline },
    { key: 'notify', label: '推送通知', icon: NotificationsOutline }
]

onMounted(async () => {
  await settingsStore.fetchSettings()
})
</script>

<template>
  <div class="settings-view">
    <header class="view-header">
      <h1 class="text-huge">系统设置</h1>
    </header>

    <div class="settings-container">
        <!-- 左侧导航 -->
        <div class="settings-nav">
            <div 
                v-for="tab in tabs" 
                :key="tab.key"
                class="nav-pill clickable"
                :class="{ active: activeTab === tab.key }"
                @click="activeTab = tab.key"
            >
                <div class="pill-icon"><n-icon :component="tab.icon" /></div>
                <span>{{ tab.label }}</span>
            </div>
        </div>

        <!-- 右侧内容 -->
        <div class="settings-content">
            <!-- Loading State -->
            <div v-if="settingsStore.isLoading || !settingsStore.settings" class="loading-wrapper">
                <n-spin size="large" description="加载配置中..." />
            </div>

            <!-- Content Components -->
            <div v-else class="tab-pane animate-fade-in">
                <GeneralSettings 
                    v-if="activeTab === 'general'" 
                    :settings="settingsStore.settings" 
                />
                <NotifySettings 
                    v-if="activeTab === 'notify'" 
                    :settings="settingsStore.settings" 
                />
            </div>
        </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  padding: 0 32px;
  max-width: 1400px;
  margin: 0 auto;
  /* 确保不使用 position: fixed 或其他可能导致层级问题的属性 */
}

.view-header {
  margin-bottom: 32px;
}

.settings-container {
    display: flex;
    gap: 40px;
    align-items: flex-start;
}

.settings-nav {
    width: 200px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.nav-pill {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 8px;
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 14px;
    transition: all 0.2s;
}

.nav-pill:hover {
    color: var(--text-primary);
    background-color: var(--sp-highlight);
}

.nav-pill.active {
    background-color: var(--sp-highlight); /* Or slightly lighter if needed */
    color: var(--text-primary);
}

.pill-icon {
    display: flex;
    font-size: 18px;
}

.settings-content {
    flex: 1;
    min-width: 0; /* 防止子组件超出 */
}

.loading-wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 300px;
}

.tab-pane {
    background-color: var(--sp-card);
    padding: 32px;
    border-radius: 12px;
}

.animate-fade-in {
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(5px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
