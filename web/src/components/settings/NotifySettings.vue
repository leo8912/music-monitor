<script setup lang="ts">
/**
 * 通知设置组件
 */

import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import type { Settings } from '@/types'
import { saveSettings, testNotify, checkNotifyStatus } from '@/api/system'
import { ref } from 'vue'

const props = defineProps<{
  settings: Settings
}>()

const message = useMessage()
const wecomStatus = ref<boolean | null>(null)

const handleSave = async () => {
  try {
    await saveSettings(props.settings)
    message.success('保存成功')
  } catch {
    message.error('保存失败')
  }
}

const handleTestWecom = async () => {
  try {
    await testNotify('wecom')
    message.success('测试消息已发送')
  } catch {
    message.error('发送失败')
  }
}

const handleCheckWecom = async () => {
  try {
    const result = await checkNotifyStatus('wecom')
    wecomStatus.value = result.connected
    message.info(result.connected ? '企业微信连接正常' : '企业微信连接失败')
  } catch {
    wecomStatus.value = false
    message.error('检查失败')
  }
}
</script>

<template>
  <div class="notify-settings" v-if="settings?.notify?.wecom">
    <h4>企业微信配置</h4>
    <n-form label-placement="left" label-width="120">
      <n-form-item label="企业ID">
        <n-input v-model:value="settings.notify.wecom.corpid" placeholder="corpid" />
      </n-form-item>
      
      <n-form-item label="应用ID">
        <n-input v-model:value="settings.notify.wecom.agentid" placeholder="agentid" />
      </n-form-item>
      
      <n-form-item label="应用密钥">
        <n-input v-model:value="settings.notify.wecom.corpsecret" type="password" placeholder="corpsecret" />
      </n-form-item>
      
      <n-form-item label="Token">
        <n-input v-model:value="settings.notify.wecom.token" placeholder="可选" />
      </n-form-item>
      
      <n-form-item label="EncodingAESKey">
        <n-input v-model:value="settings.notify.wecom.encoding_aes_key" placeholder="可选" />
      </n-form-item>
      
      <n-form-item>
        <n-button type="primary" @click="handleSave" style="margin-right: 12px">保存</n-button>
        <n-button @click="handleCheckWecom" style="margin-right: 12px">检查连接</n-button>
        <n-button @click="handleTestWecom">发送测试</n-button>
      </n-form-item>
    </n-form>
  </div>
</template>

<style scoped>
.notify-settings {
  padding: 16px;
}

h4 {
  margin-bottom: 16px;
}
</style>
