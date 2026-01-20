<script setup>
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { 
    SyncOutline, 
    NotificationsOutline, 
    MusicalNotesOutline, 
    ServerOutline,
    SettingsOutline,
    InformationCircleOutline
} from '@vicons/ionicons5'

const props = defineProps({
    activeSection: { type: String, default: 'sync' }
})

const emit = defineEmits(['update:activeSection'])

// 导航项配置
const navItems = [
    { key: 'sync', label: '同步', icon: SyncOutline },
    { key: 'notify', label: '通知', icon: NotificationsOutline },
    { key: 'playback', label: '播放', icon: MusicalNotesOutline },
    { key: 'storage', label: '存储', icon: ServerOutline },
    { key: 'general', label: '通用', icon: SettingsOutline },
]

const aboutItem = { key: 'about', label: '关于', icon: InformationCircleOutline }

const setActive = (key) => {
    emit('update:activeSection', key)
}
</script>

<template>
    <nav class="settings-sidebar">
        <div class="sidebar-nav">
            <div 
                v-for="item in navItems" 
                :key="item.key"
                class="sidebar-item"
                :class="{ active: activeSection === item.key }"
                @click="setActive(item.key)"
            >
                <n-icon :size="18" class="item-icon">
                    <component :is="item.icon" />
                </n-icon>
                <span class="item-label">{{ item.label }}</span>
            </div>
        </div>
        
        <div class="sidebar-divider"></div>
        
        <div class="sidebar-footer">
            <div 
                class="sidebar-item"
                :class="{ active: activeSection === aboutItem.key }"
                @click="setActive(aboutItem.key)"
            >
                <n-icon :size="18" class="item-icon">
                    <component :is="aboutItem.icon" />
                </n-icon>
                <span class="item-label">{{ aboutItem.label }}</span>
            </div>
        </div>
    </nav>
</template>

<style scoped>
.settings-sidebar {
    width: 180px;
    min-width: 180px;
    background: rgba(30, 30, 35, 0.92);
    backdrop-filter: blur(40px) saturate(180%);
    -webkit-backdrop-filter: blur(40px) saturate(180%);
    border-radius: 16px 0 0 16px;
    display: flex;
    flex-direction: column;
    padding: 16px 12px;
    user-select: none;
}

.sidebar-nav {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.sidebar-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 8px;
    cursor: pointer;
    color: rgba(255, 255, 255, 0.75);
    transition: all 0.15s ease;
}

.sidebar-item:hover {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.9);
}

.sidebar-item.active {
    background: rgba(250, 35, 60, 0.2);
    color: #FA233B;
}

.item-icon {
    flex-shrink: 0;
}

.item-label {
    font-size: 14px;
    font-weight: 500;
    letter-spacing: -0.01em;
}

.sidebar-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.1);
    margin: 12px 8px;
}

.sidebar-footer {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

/* 深色模式适配 */
:root[data-theme="dark"] .settings-sidebar {
    background: rgba(20, 20, 25, 0.95);
}
</style>
