<script setup>
/**
 * 设置模态框 - 双面板 macOS 风格
 * 重设计版本
 */
import { ref, watch, computed } from 'vue'
import { NModal, useMessage } from 'naive-ui'
import axios from 'axios'

// 组件导入
import SettingsSidebar from './SettingsSidebar.vue'
import SyncSettings from './sections/SyncSettings.vue'
import NotifySettings from './sections/NotifySettings.vue'
import GeneralSettings from './sections/GeneralSettings.vue'
import AboutSettings from './sections/AboutSettings.vue'
import StorageSettings from './sections/StorageSettings.vue'

const props = defineProps({
    show: { type: Boolean, default: false }
})

const emit = defineEmits(['update:show'])

const message = useMessage()

// 当前激活的面板
const activeSection = ref('sync')

// 设置数据
const settings = ref({
    monitor: {},
    notify: {},
    general: {}
})

// 日志数据（底部面板用）
const logs = ref([])
const showLogPanel = computed(() => settings.value.general?.show_log_panel ?? false)

// 加载配置
const loadSettings = async () => {
    try {
        const res = await axios.get('/api/settings')
        settings.value = res.data
    } catch (e) {
        console.error('Failed to load settings:', e)
    }
}

// 保存配置（自动保存）
let saveTimeout = null
const saveSettings = async () => {
    if (saveTimeout) clearTimeout(saveTimeout)
    saveTimeout = setTimeout(async () => {
        try {
            await axios.post('/api/settings', settings.value)
            // 静默保存，不显示消息
        } catch (e) {
            message.error('保存失败: ' + e.message)
        }
    }, 500) // 防抖 500ms
}

// 监听设置变化自动保存
watch(settings, saveSettings, { deep: true })

// 模态框打开时加载设置
watch(() => props.show, (val) => {
    if (val) {
        loadSettings()
    }
})

// 加载日志
const loadLogs = async () => {
    try {
        const res = await axios.get('/api/logs')
        logs.value = res.data.logs || []
    } catch (e) {
        console.error('Failed to load logs:', e)
    }
}

// 日志轮询
let logInterval = null
watch(showLogPanel, (val) => {
    if (val) {
        loadLogs()
        logInterval = setInterval(loadLogs, 3000)
    } else {
        if (logInterval) clearInterval(logInterval)
    }
})
</script>

<template>
    <n-modal 
        :show="show" 
        @update:show="emit('update:show', $event)" 
        class="settings-modal-v2"
        :mask-closable="true"
    >
        <div class="settings-container">
            <!-- 侧边栏 -->
            <SettingsSidebar 
                v-model:activeSection="activeSection"
            />
            
            <!-- 内容区 -->
            <div class="settings-content">
                <!-- 头部 -->
                <div class="content-header">
                    <h1 class="content-title">
                        {{ activeSection === 'sync' ? '同步' : '' }}
                        {{ activeSection === 'notify' ? '通知' : '' }}
                        {{ activeSection === 'playback' ? '播放' : '' }}
                        {{ activeSection === 'storage' ? '存储' : '' }}
                        {{ activeSection === 'general' ? '通用' : '' }}
                        {{ activeSection === 'about' ? '关于' : '' }}
                    </h1>
                    <button class="close-btn" @click="emit('update:show', false)">✕</button>
                </div>
                
                <!-- 面板内容 -->
                <div class="content-body">
                    <SyncSettings 
                        v-if="activeSection === 'sync'"
                        :settings="settings"
                        @update:settings="settings = $event"
                    />
                    
                    <NotifySettings 
                        v-if="activeSection === 'notify'"
                        :settings="settings"
                        @update:settings="settings = $event"
                    />
                    
                    <GeneralSettings 
                        v-if="activeSection === 'general'"
                        :settings="settings"
                        @update:settings="settings = $event"
                    />
                    
                    <AboutSettings 
                        v-if="activeSection === 'about'"
                    />
                    
                    <!-- 占位 - 播放和存储面板 -->
                    <div v-if="activeSection === 'playback'" class="placeholder-section">
                        <p>🎧 播放设置</p>
                        <span>即将推出</span>
                    </div>
                    
                    <div v-if="activeSection === 'storage'" class="storage-section-wrapper">
                         <StorageSettings 
                            :settings="settings"
                            @update:settings="settings = $event"
                         />
                    </div>
                </div>
                
                <!-- 底部日志面板（可选） -->
                <div v-if="showLogPanel" class="log-panel">
                    <div class="log-header">
                        <span>系统日志</span>
                        <button @click="loadLogs">刷新</button>
                    </div>
                    <div class="log-content">
                        <div v-for="(log, i) in logs.slice(-50)" :key="i" class="log-line">
                            {{ log }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </n-modal>
</template>

<style scoped>
.settings-container {
    display: flex;
    width: 860px;
    max-width: 90vw;
    height: 640px;
    max-height: 85vh;
    background: var(--bg-card, #ffffff);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 
        0 40px 100px rgba(0, 0, 0, 0.25),
        0 0 0 1px rgba(0, 0, 0, 0.05);
}

.settings-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.content-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 24px 16px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.content-title {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary, #1d1d1f);
    margin: 0;
}

.close-btn {
    width: 28px;
    height: 28px;
    border: none;
    background: rgba(0, 0, 0, 0.05);
    border-radius: 50%;
    font-size: 14px;
    color: var(--text-secondary, #86868b);
    cursor: pointer;
    transition: all 0.15s;
}

.close-btn:hover {
    background: rgba(0, 0, 0, 0.1);
    color: var(--text-primary, #1d1d1f);
}

.content-body {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
}

.placeholder-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-secondary, #86868b);
}

.placeholder-section p {
    font-size: 32px;
    margin: 0 0 8px;
}

.placeholder-section span {
    font-size: 14px;
    opacity: 0.6;
}

/* 日志面板 */
.log-panel {
    border-top: 1px solid rgba(0, 0, 0, 0.08);
    background: rgba(30, 30, 35, 0.95);
    max-height: 150px;
}

.log-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 16px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.6);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.log-header button {
    background: none;
    border: none;
    color: #007AFF;
    font-size: 12px;
    cursor: pointer;
}

.log-content {
    padding: 8px 16px;
    font-family: var(--font-mono, monospace);
    font-size: 11px;
    color: rgba(255, 255, 255, 0.8);
    overflow-y: auto;
    max-height: 100px;
}

.log-line {
    white-space: nowrap;
    line-height: 1.6;
}

/* 深色模式 */
:root[data-theme="dark"] .settings-container {
    background: #1c1c1e;
}

:root[data-theme="dark"] .content-header {
    border-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .content-title {
    color: #f5f5f7;
}

:root[data-theme="dark"] .close-btn {
    background: rgba(255, 255, 255, 0.1);
    color: #98989d;
}

:root[data-theme="dark"] .close-btn:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #f5f5f7;
}
</style>
