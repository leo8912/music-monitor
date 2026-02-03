<script setup lang="ts">
/**
 * 通用设置组件 - Spotify 风格增强版
 * 功能：基础配置管理 + 数据深度维护 (扫描/补全/刷新)
 */
import { NForm, NFormItem, NInput, NInputNumber, NButton, useMessage, useDialog, NDivider, NSpace, NSpin, NIcon, NTag } from 'naive-ui'
import { 
    ReloadOutline, 
    BuildOutline, 
    CloudDownloadOutline, 
    SaveOutline,
    SearchOutline,
    TrashBinOutline
} from '@vicons/ionicons5'
import type { Settings } from '@/types'
import { saveSettings, resetDatabase } from '@/api/system'
import { enrichLocalFiles, refreshLibraryMetadata, scanLibrary } from '@/api/library'
import { ref } from 'vue'

const props = defineProps<{
  settings: Settings
}>()

const message = useMessage()
const dialog = useDialog()

// 任务状态
const scanning = ref(false)
const enrichingLocal = ref(false)
const refreshingLib = ref(false)

const saving = ref(false)

// 1. 保存基础设置
const handleSave = async () => {
  saving.value = true
  try {
    if (!props.settings) return
    await saveSettings(props.settings)
    message.success('配置已保存并同步')
  } catch {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 2. 扫描本地目录
const handleScan = async () => {
    if (scanning.value) return
    scanning.value = true
    try {
        const res = await scanLibrary()
        if (res.new_files_found !== undefined) {
             message.success(`扫描完成，发现 ${res.new_files_found} 个新文件`)
        }
    } catch (e) {
        message.error('扫描任务执行失败')
    } finally {
        scanning.value = false
    }
}

// 3. 本地标签补全 (ID3/FLAC)
const handleEnrichLocal = async () => {
    if (enrichingLocal.value) return
    enrichingLocal.value = true
    try {
        const res = await enrichLocalFiles(20)
        if (res.success) {
            message.success(`本地标签补全成功，已修复 ${res.enriched_count} 首歌曲`)
        }
    } catch (e) {
        message.error('标签补全任务失败')
    } finally {
        enrichingLocal.value = false
    }
}

// 4. 同步云端元数据 (封面/专辑)
const handleRefreshLibrary = async () => {
    if (refreshingLib.value) return
    refreshingLib.value = true
    try {
        const res = await refreshLibraryMetadata(50)
        if (res.success) {
            message.success(`云端元数据同步完成，更新了 ${res.enriched_count} 条记录`)
        }
    } catch (e) {
        message.error('云端同步任务失败')
    } finally {
        refreshingLib.value = false
    }
}

// 5. 重置数据库
const resetting = ref(false)
const handleResetDatabase = async () => {
    dialog.warning({
        title: '危险操作',
        content: '确定要清空数据库吗？\n这将删除所有歌曲和歌手的元数据缓存。\n\n注意：\n1. 本地音频文件不会被删除\n2. 您需要重新扫描或刷新页面以重建数据',
        positiveText: '确定重置',
        negativeText: '取消',
        onPositiveClick: async () => {
            resetting.value = true
            try {
                const res = await resetDatabase()
                if (res.status === 'success') {
                    message.success('数据库已重置')
                    // 自动刷新页面或触发重新扫描? 用户最好手动刷新页面
                    setTimeout(() => window.location.reload(), 1500)
                }
            } catch (e) {
                message.error('重置失败')
            } finally {
                resetting.value = false
            }
        }
    })
}
</script>

<template>
  <div class="general-settings" v-if="settings">
    <n-form label-placement="left" label-width="170" class="settings-form">
      <div class="settings-section">
          <div class="section-header">
              <span class="section-title">基础运行配置</span>
              <n-tag :bordered="false" type="info" size="small">核心</n-tag>
          </div>
          
          <n-form-item label="外部访问 URL" v-if="settings.system">
            <n-input v-model:value="settings.system.external_url" placeholder="http://192.168.1.100:5173" />
            <template #feedback>用于生成外部预览链接预览歌曲</template>
          </n-form-item>
          
          <n-form-item label="默认监控间隔 (分)" v-if="settings.monitor">
            <n-input-number v-model:value="settings.monitor.interval" :min="1" :max="1440" />
          </n-form-item>
          
          <n-form-item label="首选音质 (Kbps)" v-if="settings.download">
            <n-input-number v-model:value="settings.download.quality_preference" :min="128" :max="3000" :step="128" />
          </n-form-item>

          <div class="action-bar">
              <n-button type="primary" :loading="saving" @click="handleSave">
                  <template #icon><n-icon :component="SaveOutline" /></template>
                  保存配置
              </n-button>
          </div>
      </div>

      <n-divider />

      <div class="settings-section">
          <div class="section-header">
              <span class="section-title">媒体库维护工具</span>
              <n-tag :bordered="false" type="success" size="small">Data</n-tag>
          </div>
          
          <div class="data-actions-grid">
              <!-- 1. 扫描 -->
              <div class="data-card clickable" @click="handleScan">
                  <div class="card-icon"><n-icon :component="ReloadOutline" :class="{ 'spin': scanning }" /></div>
                  <div class="card-info">
                      <div class="card-title">扫描本地目录</div>
                      <div class="card-desc">发现 audio_cache 和 favorites 文件夹中的新文件</div>
                  </div>
                  <n-button quaternary size="small" :loading="scanning">执行</n-button>
              </div>

              <!-- 2. 补全标签 -->
              <div class="data-card clickable" @click="handleEnrichLocal">
                  <div class="card-icon"><n-icon :component="BuildOutline" :class="{ 'pulse': enrichingLocal }" /></div>
                  <div class="card-info">
                      <div class="card-title">补全本地标签</div>
                      <div class="card-desc">尝试将封面、歌词写入本地 MP3/FLAC 文件的 ID3 信息</div>
                  </div>
                   <n-button quaternary size="small" :loading="enrichingLocal">执行</n-button>
              </div>

              <!-- 3. 同步元数据 -->
              <div class="data-card clickable" @click="handleRefreshLibrary">
                  <div class="card-icon"><n-icon :component="CloudDownloadOutline" :class="{ 'bounce': refreshingLib }" /></div>
                  <div class="card-info">
                      <div class="card-title">同步云端元数据</div>
                      <div class="card-desc">从网易云/QQ音乐同步缺失的封面、专辑、发布日期</div>
                  </div>
                  <n-button quaternary size="small" :loading="refreshingLib">执行</n-button>
              </div>

              <!-- 4. 重置数据库 -->
              <div class="data-card clickable warning-card" @click="handleResetDatabase">
                  <div class="card-icon"><n-icon :component="TrashBinOutline" /></div>
                  <div class="card-info">
                      <div class="card-title">重置数据库</div>
                      <div class="card-desc">清空所有元数据缓存 (不删除文件)，用于彻底修复数据问题</div>
                  </div>
                   <n-button quaternary type="error" size="small" :loading="resetting">重置</n-button>
              </div>
          </div>
      </div>
    </n-form>
  </div>
  
  <div v-else class="loading-state">
      <n-spin size="large" description="正在解析配置树..." />
  </div>
</template>

<style scoped>
.general-settings {
  padding-bottom: 40px;
}

.settings-form {
    max-width: 800px;
}

.settings-section {
    margin-bottom: 24px;
}

.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
}

.section-title {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    border-left: 4px solid var(--sp-green);
    padding-left: 12px;
}

.action-bar {
    margin-top: 24px;
    display: flex;
    justify-content: flex-end;
}

/* Data Cards Grid */
.data-actions-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
}

.data-card {
    display: flex;
    align-items: center;
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 16px 20px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.data-card:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border-color: var(--sp-green);
    transform: translateY(-2px);
}

.card-icon {
    font-size: 24px;
    margin-right: 20px;
    color: var(--sp-green);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
}

.card-info {
    flex: 1;
}

.card-title {
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 2px;
}

.card-desc {
    font-size: 12px;
    color: var(--text-secondary);
}

/* Animations */
.spin {
    animation: sp-spin 2s linear infinite;
}

.pulse {
    animation: sp-pulse 1.5s ease-in-out infinite;
}

.bounce {
    animation: sp-bounce 1s infinite alternate;
}

@keyframes sp-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

@keyframes sp-pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

@keyframes sp-bounce {
    from { transform: translateY(0); }
    to { transform: translateY(-4px); }
}


.loading-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 300px;
}

.warning-card {
    border-color: rgba(232, 128, 128, 0.2);
}

.warning-card:hover {
    background-color: rgba(232, 128, 128, 0.08);
    border-color: #d03050;
}
</style>
