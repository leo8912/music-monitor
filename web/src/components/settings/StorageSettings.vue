<script setup lang="ts">
/**
 * 存储设置组件
 */

import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import type { Settings } from '@/types'
import { saveSettings } from '@/api/system'
import { scanLibrary } from '@/api/library'

const props = defineProps<{
  settings: Settings
}>()

const message = useMessage()

const handleScan = async () => {
  try {
    const result = await scanLibrary()
    message.success(`扫描完成：发现 ${result.new_files_found || 0} 个新文件`)
  } catch {
    message.error('扫描失败')
  }
}
</script>

<template>
  <div class="storage-settings">
    <n-form label-placement="left" label-width="120">
      <n-form-item label="收藏目录">
        <n-input v-model:value="settings.storage!.favorites_dir" placeholder="favorites" />
      </n-form-item>
      
      <n-form-item>
        <n-button type="primary" @click="handleScan">扫描本地文件</n-button>
      </n-form-item>
    </n-form>
  </div>
</template>

<style scoped>
.storage-settings {
  padding: 16px;
}
</style>
