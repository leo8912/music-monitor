<script setup>
/**
 * ⚙️ 通用设置面板
 * 包含主题切换、语言和调试选项
 * 注意：后端使用 'global' 键名，组件需健壮处理空值
 */
import { computed, watch, onMounted } from 'vue'
import SettingSwitch from '../controls/SettingSwitch.vue'
import SettingSelect from '../controls/SettingSelect.vue'
import SettingInput from '../controls/SettingInput.vue'

import { saveTheme, themePreference } from '../../../utils/theme'

const props = defineProps({
    settings: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:settings'])

// 主题选项
const themeOptions = [
    { value: 'light', label: '浅色' },
    { value: 'dark', label: '深色' },
    { value: 'auto', label: '跟随系统' }
]

// 日志级别选项
const logLevelOptions = [
    { value: 'DEBUG', label: 'DEBUG' },
    { value: 'INFO', label: 'INFO' },
    { value: 'WARNING', label: 'WARNING' },
    { value: 'ERROR', label: 'ERROR' }
]

// 安全获取全局配置
const getGlobalConfig = () => {
    if (!props.settings) return {}
    return props.settings.global || props.settings.general || {}
}

// 获取主题配置 (使用全局响应式状态)
const themeValue = computed(() => themePreference.value)

// 获取日志级别
const logLevelValue = computed(() => {
    const config = getGlobalConfig()
    return config.log_level || 'INFO'
})

// 获取外部链接
const externalUrlValue = computed(() => {
    const config = getGlobalConfig()
    return config.external_url || ''
})

// 获取日志面板开关
const showLogPanelValue = computed(() => {
    const config = getGlobalConfig()
    return config.show_log_panel === true
})

// 监听后端配置变化 (仅当非初始加载时同步)
watch(() => getGlobalConfig().theme, (newBackendTheme) => {
    if (newBackendTheme && newBackendTheme !== themePreference.value) {
        saveTheme(newBackendTheme)
    }
})

// 更新设置 - 使用 global 键名以匹配后端
const updateGeneral = (key, value) => {
    // 如果是主题，立即应用本地效果
    if (key === 'theme') {
        saveTheme(value)
    }

    const currentGlobal = getGlobalConfig()
    emit('update:settings', {
        ...props.settings,
        global: {
            ...currentGlobal,
            [key]: value
        }
    })
}


</script>

<template>
    <div class="settings-section">
        <!-- 外观 -->
        <h2 class="section-title">外观</h2>
        <div class="section-card">
            <SettingSelect
                :model-value="themeValue"
                label="主题"
                :options="themeOptions"
                @update:model-value="updateGeneral('theme', $event)"
            />
        </div>
        


        <!-- 网络 -->
        <h2 class="section-title">网络</h2>
        <div class="section-card">
            <SettingInput
                :model-value="externalUrlValue"
                label="远程访问地址"
                placeholder="例如 http://my-nas:8000"
                description="设置后，推送通知将包含跳转到此地址的播放链接"
                @update:model-value="updateGeneral('external_url', $event)"
            />
        </div>
        


        <!-- 调试 -->
        <h2 class="section-title">调试</h2>
        <div class="section-card">
            <SettingSelect
                :model-value="logLevelValue"
                label="日志级别"
                :options="logLevelOptions"
                @update:model-value="updateGeneral('log_level', $event)"
            />
            
            <SettingSwitch
                :model-value="showLogPanelValue"
                label="显示日志面板"
                description="在设置底部显示实时日志"
                @update:model-value="updateGeneral('show_log_panel', $event)"
            />
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

.section-title:not(:first-child) {
    margin-top: 32px;
}

.section-card {
    background: rgba(0, 0, 0, 0.03);
    border-radius: 16px;
    overflow: hidden;
}

/* 深色模式 */
:root[data-theme="dark"] .section-card {
    background: rgba(255, 255, 255, 0.05);
}
</style>
