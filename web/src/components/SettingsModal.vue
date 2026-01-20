<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import axios from 'axios'
import { 
    NModal, NTabs, NTabPane, NSwitch, NInput, NInputNumber, NButton, NIcon, NSelect, useMessage 
} from 'naive-ui'
import { CloseOutline, RefreshOutline } from '@vicons/ionicons5'

const props = defineProps({
  show: { type: Boolean, default: false }
})

const emit = defineEmits(['update:show'])

const message = useMessage()
const activeSettingsTab = ref('monitor')
const savingSettings = ref(false)
const testingNotify = ref(null)

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

// Logs State
const logs = ref([])
const refreshingLogs = ref(false)
const logContainer = ref(null)
let logPoller = null

const activeNotifyChannel = ref('wecom')
const channelConfig = computed(() => {
    if (!settingsForm.value.notify) return {}
    return settingsForm.value.notify[activeNotifyChannel.value] || {}
})

const checkingStatus = ref(false)
const channelStatus = ref({ wecom: null, telegram: null })

const getServiceName = (key) => {
    const maps = { 'netease': '网易云音乐', 'qqmusic': 'QQ 音乐' }
    return maps[key] || key
}

const fetchSettings = async () => {
    try {
        const res = await axios.get('/api/settings')
        settingsForm.value = res.data
    } catch (e) {
        message.error('加载配置失败')
    }
}

const saveSettings = async () => {
    savingSettings.value = true
    try {
        await axios.post('/api/settings', settingsForm.value)
        message.success('配置已保存 (部分设置可能需要重启生效)')
        emit('update:show', false)
    } catch (e) {
        message.error('保存失败: ' + e.message)
    } finally {
        savingSettings.value = false
    }
}

// Log Logic
const fetchLogs = async () => {
    try {
        const res = await axios.get('/api/logs')
        
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

const startLogPolling = () => {
    if (logPoller) clearInterval(logPoller)
    fetchLogs()
    logPoller = setInterval(fetchLogs, 2000)
}

const stopLogPolling = () => {
    if (logPoller) {
        clearInterval(logPoller)
        logPoller = null
    }
}

// Notify Check
const checkChannelStatus = async (channel) => {
    checkingStatus.value = true
    try {
        await axios.post('/api/settings', settingsForm.value) // Save first
        const res = await axios.get(`/api/check_notify_status/${channel}`)
        channelStatus.value[channel] = res.data.connected
        if (res.data.connected) {
            message.success(`${channel === 'wecom' ? '企业微信' : 'Telegram'} 连接正常 🟢`)
        } else {
            message.warning("连接测试失败 🔴，请检查配置")
        }
    } catch (e) {
        channelStatus.value[channel] = false
        message.error("连接检测出错: " + e.message)
    } finally {
        checkingStatus.value = false
    }
}

const testNotify = async (channel) => {
    try {
        testingNotify.value = channel
        await axios.post('/api/settings', settingsForm.value)
        const res = await axios.post(`/api/test_notify/${channel}`)
        message.success(res.data.message)
    } catch (e) {
        message.error("测试失败: " + (e.response?.data?.detail || e.message))
    } finally {
        testingNotify.value = null
    }
}

// Watch visibility
watch(() => props.show, (val) => {
    if (val) {
        fetchSettings()
    } else {
        stopLogPolling()
    }
})

// Watch Tabs for Logging
watch(activeSettingsTab, (tab) => {
    if (props.show && tab === 'logs') {
        startLogPolling()
    } else {
        stopLogPolling()
    }
})

</script>

<template>
    <n-modal :show="show" @update:show="$emit('update:show', $event)" class="settings-modal-ios" :mask-closable="true">
        <div class="ios-settings-container">
            <!-- Header -->
            <div class="ios-header">
                <div class="ios-title">⚙️ 控制中心</div>
                <div class="ios-close-btn" @click="$emit('update:show', false)">
                    <n-icon size="20"><CloseOutline /></n-icon>
                </div>
            </div>

            <!-- Content -->
            <div class="ios-content">
                <n-tabs v-model:value="activeSettingsTab" type="segment" animated class="ios-tabs">
                    <!-- Tab 1: Monitor Services -->
                    <n-tab-pane name="monitor" tab="📡 监听源">
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
                    <n-tab-pane name="notify" tab="🔔 推送通道">
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
                        
                        <div class="ios-group" v-if="channelConfig">
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
</template>

<style scoped>
@import '../assets/ios-settings.css';

/* Log Console Specific Overrides */
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
</style>
