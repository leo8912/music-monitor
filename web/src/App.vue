<script setup>
import { onMounted, computed } from 'vue'
import { NConfigProvider, NGlobalStyle, NMessageProvider, darkTheme } from 'naive-ui'
import { initTheme, themeMode } from './utils/theme'

const appTheme = computed(() => themeMode.value === 'dark' ? darkTheme : null)

// Apple Music Style Overrides
const themeOverrides = computed(() => {
    if (themeMode.value === 'dark') {
        return {
            common: {
                bodyColor: '#000000',
                cardColor: '#1C1C1E',
                modalColor: '#1C1C1E',
                popoverColor: '#1C1C1E'
            }
        }
    }
    return null
})

onMounted(() => {
  initTheme()
})
</script>

<template>
  <n-config-provider :theme="appTheme" :theme-overrides="themeOverrides">
    <n-global-style />
    <n-message-provider>
      <router-view />
    </n-message-provider>
  </n-config-provider>
</template>
