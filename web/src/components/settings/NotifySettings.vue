<script setup lang="ts">
/**
 * 通知设置组件
 */

import { NForm, NFormItem, NInput, NButton, useMessage, NSwitch, NDivider, NSpace } from 'naive-ui'
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
  <div class="notify-settings" v-if="settings?.notify">
    
    <!-- WeCom Config -->
    <div class="section">
        <div class="section-header">
            <h4>企业微信配置</h4>
            <n-switch v-model:value="settings.notify.wecom.enabled" size="small" />
        </div>
        
        <n-form label-placement="left" label-width="120" v-if="settings.notify.wecom.enabled">
        <n-form-item label="企业ID (CorpID)">
            <n-input v-model:value="settings.notify.wecom.corp_id" placeholder="ww..." />
        </n-form-item>
        
        <n-form-item label="应用ID (AgentID)">
            <n-input v-model:value="settings.notify.wecom.agent_id" placeholder="1000001" />
        </n-form-item>
        
        <n-form-item label="应用密钥 (Secret)">
            <n-input v-model:value="settings.notify.wecom.secret" type="password" placeholder="corpsecret" />
        </n-form-item>
        
        <n-form-item label="Token">
            <n-input v-model:value="settings.notify.wecom.token" placeholder="可选 (如果使用回调)" />
        </n-form-item>
        
        <n-form-item label="EncodingAESKey">
            <n-input v-model:value="settings.notify.wecom.encoding_aes_key" placeholder="可选 (如果使用回调)" />
        </n-form-item>
        
        <n-form-item>
            <n-space>
                <n-button type="primary" @click="handleSave">保存</n-button>
                <n-button @click="handleCheckWecom">检查连接</n-button>
                <n-button @click="handleTestWecom">发送测试</n-button>
            </n-space>
        </n-form-item>
        </n-form>
    </div>
    
    <n-divider />

    <!-- Telegram Config -->
    <div class="section">
        <div class="section-header">
            <h4>Telegram Bot 配置</h4>
            <n-switch v-model:value="settings.notify.telegram.enabled" size="small" />
        </div>
        
        <n-form label-placement="left" label-width="120" v-if="settings.notify.telegram.enabled">
            <n-form-item label="Bot Token">
                <n-input v-model:value="settings.notify.telegram.bot_token" type="password" placeholder="123456:ABC-..." />
            </n-form-item>
            
            <n-form-item label="Chat ID">
                <n-input v-model:value="settings.notify.telegram.chat_id" placeholder="-100..." />
            </n-form-item>
            
            <n-form-item>
                <n-space>
                    <n-button type="primary" @click="handleSave">保存</n-button>
                    <!-- <n-button @click="handleTestTelegram">发送测试</n-button> -->
                </n-space>
            </n-form-item>
        </n-form>
    </div>

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
