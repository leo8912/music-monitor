<script setup>
/**
 * 🎵 同步设置面板
 */
import { ref, watch } from 'vue'
import { NIcon, NButton } from 'naive-ui'
import { RefreshOutline, CheckmarkCircle, CloseCircle } from '@vicons/ionicons5'
import SettingSwitch from '../controls/SettingSwitch.vue'
import SettingInput from '../controls/SettingInput.vue'

const props = defineProps({
    settings: { type: Object, required: true }
})

const emit = defineEmits(['update:settings'])

// 本地状态
const loading = ref({ netease: false, qqmusic: false })

// 触发立即同步
const triggerSync = async (source) => {
    loading.value[source] = true
    try {
        await fetch(`/api/run_check/${source}`, { method: 'POST' })
    } finally {
        loading.value[source] = false
    }
}

// 更新设置
const updateSetting = (source, key, value) => {
    emit('update:settings', {
        ...props.settings,
        monitor: {
            ...props.settings.monitor,
            [source]: {
                ...props.settings.monitor?.[source],
                [key]: value
            }
        }
    })
}
</script>

<template>
    <div class="settings-section">
        <h2 class="section-title">音乐源</h2>
        
        <!-- 网易云音乐 -->
        <div class="section-card">
            <div class="source-header">
                <div class="source-logo netease">
                    <svg viewBox="0 0 100 100" width="32" height="32">
                        <circle cx="50" cy="50" r="50" fill="#E60026"/>
                        <path d="M50 20c-16.5 0-30 13.5-30 30 0 12.4 7.6 23 18.4 27.5.3-2.4.6-6.1-.1-8.7-.6-2.4-4.2-17.8-4.2-17.8s-1.1-2.1-1.1-5.3c0-5 2.9-8.7 6.5-8.7 3.1 0 4.5 2.3 4.5 5 0 3.1-2 7.7-3 12-0.8 3.5 1.8 6.4 5.3 6.4 6.3 0 11.2-6.7 11.2-16.3 0-8.5-6.1-14.5-14.9-14.5-10.1 0-16.1 7.6-16.1 15.5 0 3.1 1.2 6.4 2.7 8.2.3.4.3.7.2 1.1l-1 4.2c-.2.7-.6.9-1.3.5-4.8-2.2-7.8-9.3-7.8-15 0-12.2 8.9-23.4 25.6-23.4 13.4 0 23.9 9.6 23.9 22.4 0 13.4-8.4 24.1-20.1 24.1-3.9 0-7.6-2-8.9-4.5l-2.4 9.2c-.9 3.4-3.2 7.6-4.8 10.2C44.5 79.6 47.2 80 50 80c16.5 0 30-13.5 30-30S66.5 20 50 20z" fill="white"/>
                    </svg>
                </div>
                <span class="source-name">网易云音乐</span>
                <span class="source-status" v-if="settings.monitor?.netease?.enabled">
                    <n-icon :size="14"><CheckmarkCircle /></n-icon>
                    运行中
                </span>
            </div>
            
            <SettingSwitch
                :model-value="settings.monitor?.netease?.enabled ?? true"
                label="自动同步"
                @update:model-value="updateSetting('netease', 'enabled', $event)"
            />
            
            <SettingInput
                :model-value="settings.monitor?.netease?.interval ?? 60"
                label="同步间隔"
                type="number"
                suffix="分钟"
                @update:model-value="updateSetting('netease', 'interval', $event)"
            />
            
            <div class="setting-row info-row">
                <span class="setting-label">订阅歌手</span>
                <span class="setting-value">{{ settings.monitor?.netease?.users?.length || 0 }} 位</span>
            </div>
            
            <div class="card-footer">
                <n-button 
                    size="small" 
                    quaternary 
                    :loading="loading.netease"
                    @click="triggerSync('netease')"
                >
                    <template #icon><n-icon><RefreshOutline /></n-icon></template>
                    立即同步
                </n-button>
            </div>
        </div>
        
        <!-- QQ 音乐 -->
        <div class="section-card">
            <div class="source-header">
                <div class="source-logo qqmusic">
                    <svg viewBox="0 0 100 100" width="32" height="32">
                        <circle cx="50" cy="50" r="50" fill="#31C27C"/>
                        <g fill="white">
                            <ellipse cx="50" cy="42" rx="22" ry="24"/>
                            <path d="M35 60c-3 8-2 15 0 18 2 3 8 4 15 2s12-3 15-2c3 1 5 0 5-3 0-4-2-10-5-15"/>
                            <circle cx="42" cy="38" r="4" fill="#31C27C"/>
                            <circle cx="58" cy="38" r="4" fill="#31C27C"/>
                        </g>
                    </svg>
                </div>
                <span class="source-name">QQ 音乐</span>
                <span class="source-status" v-if="settings.monitor?.qqmusic?.enabled">
                    <n-icon :size="14"><CheckmarkCircle /></n-icon>
                    运行中
                </span>
            </div>
            
            <SettingSwitch
                :model-value="settings.monitor?.qqmusic?.enabled ?? true"
                label="自动同步"
                @update:model-value="updateSetting('qqmusic', 'enabled', $event)"
            />
            
            <SettingInput
                :model-value="settings.monitor?.qqmusic?.interval ?? 60"
                label="同步间隔"
                type="number"
                suffix="分钟"
                @update:model-value="updateSetting('qqmusic', 'interval', $event)"
            />
            
            <div class="setting-row info-row">
                <span class="setting-label">订阅歌手</span>
                <span class="setting-value">{{ settings.monitor?.qqmusic?.users?.length || 0 }} 位</span>
            </div>
            
            <div class="card-footer">
                <n-button 
                    size="small" 
                    quaternary 
                    :loading="loading.qqmusic"
                    @click="triggerSync('qqmusic')"
                >
                    <template #icon><n-icon><RefreshOutline /></n-icon></template>
                    立即同步
                </n-button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.settings-section {
    padding: 24px;
}

.section-title {
    font-size: 13px;
    font-weight: 600;
    color: #86868B;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 16px 4px;
}

.section-card {
    background: rgba(0, 0, 0, 0.03);
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 16px;
}

.source-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.source-logo {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    overflow: hidden;
    flex-shrink: 0;
}

.source-logo svg {
    display: block;
}

.source-name {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary, #1d1d1f);
    flex: 1;
}

.source-status {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #34C759;
}

.setting-row.info-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.setting-label {
    font-size: 15px;
    font-weight: 500;
    color: var(--text-primary, #1d1d1f);
}

.setting-value {
    font-size: 14px;
    color: var(--text-secondary, #86868b);
}

.card-footer {
    padding: 12px 16px;
    display: flex;
    justify-content: flex-end;
}

/* 深色模式 */
:root[data-theme="dark"] .section-card {
    background: rgba(255, 255, 255, 0.05);
}

:root[data-theme="dark"] .source-header,
:root[data-theme="dark"] .setting-row.info-row {
    border-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .source-name,
:root[data-theme="dark"] .setting-label {
    color: #f5f5f7;
}
</style>
