<script setup>
/**
 * 💾 存储设置面板
 * 管理缓存、收藏目录和清理策略
 */
import { ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import SettingInput from '../controls/SettingInput.vue'
import SettingSwitch from '../controls/SettingSwitch.vue'

const props = defineProps({
    settings: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:settings'])
const message = useMessage()
const saving = ref(false)

const getStorageConfig = () => {
    if (!props.settings) return {}
    return props.settings.storage || {}
}

const cacheDirValue = computed(() => getStorageConfig().cache_dir || '/audio_cache')
const favoritesDirValue = computed(() => getStorageConfig().favorites_dir || '/favorites')
const libraryPathValue = computed(() => getStorageConfig().library_path || '')
const retentionDaysValue = computed(() => getStorageConfig().retention_days || 180)
const autoCacheEnabledValue = computed(() => getStorageConfig().auto_cache_enabled !== false)

const updateStorage = (key, value) => {
    const currentStorage = getStorageConfig()
    emit('update:settings', {
        ...props.settings,
        storage: {
            ...currentStorage,
            [key]: value
        }
    })
}

// 手动保存功能
const handleSave = async () => {
    saving.value = true
    try {
        await axios.post('/api/settings', props.settings)
        message.success("存储设置已保存")
    } catch (e) {
        message.error("保存失败: " + e.message)
    } finally {
        saving.value = false
    }
}
</script>

<template>
    <div class="settings-section">
        <h2 class="section-title">存储路径</h2>
        <div class="section-card">
            <SettingInput
                :model-value="cacheDirValue"
                label="缓存目录"
                placeholder="/audio_cache"
                description="用于存放下载的音频文件。Docker 环境下建议使用 /audio_cache 并挂载卷。"
                @update:model-value="updateStorage('cache_dir', $event)"
            />
             <SettingInput
                :model-value="favoritesDirValue"
                label="收藏目录"
                placeholder="/favorites"
                description="歌曲被收藏后将复制到此目录。Docker 环境下建议使用 /favorites 并挂载卷。"
                @update:model-value="updateStorage('favorites_dir', $event)"
            />
            <SettingInput
                :model-value="libraryPathValue"
                label="本地音乐库"
                placeholder="例如 D:/Music"
                description="如果您已经有下载好的音乐库，在此填入路径。系统下载前会优先检查此目录是否存在歌曲。"
                @update:model-value="updateStorage('library_path', $event)"
            />
        </div>

        <h2 class="section-title">清理策略</h2>
        <div class="section-card">
            <SettingInput
                :model-value="retentionDaysValue"
                label="缓存保留天数"
                placeholder="180"
                type="number"
                suffix="天"
                description="系统将自动缓存最近 X 天内发布的歌曲。超过此时间范围的旧歌缓存将被自动清理。设置为 0 则禁用此功能。"
                @update:model-value="updateStorage('retention_days', parseInt($event, 10))"
            />
            <SettingSwitch
                :model-value="autoCacheEnabledValue"
                label="自动补全功能"
                description="自动下载最近发布的歌曲到本地缓存。根据上方设置的保留天数自动补全歌曲文件。"
                @update:model-value="updateStorage('auto_cache_enabled', $event)"
            />
        </div>

        <div class="actions-footer">
            <button class="save-btn" :disabled="saving" @click="handleSave">
                <span v-if="saving">保存中...</span>
                <span v-else>保存更改</span>
            </button>
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

.actions-footer {
    margin-top: 32px;
    display: flex;
    justify-content: flex-end;
}

.save-btn {
    background: #007AFF;
    color: white;
    font-weight: 600;
    padding: 10px 24px;
    border-radius: 20px; /* Pill shape */
    border: none;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
}

.save-btn:hover:not(:disabled) {
    background: #006add;
    transform: translateY(-1px);
}

.save-btn:disabled {
    background: rgba(0, 0, 0, 0.2);
    cursor: not-allowed;
    box-shadow: none;
}

/* 深色模式 */
:root[data-theme="dark"] .section-card {
    background: rgba(255, 255, 255, 0.05);
}
</style>
