<script setup>
import { NConfigProvider, NGlobalStyle, NMessageProvider } from 'naive-ui'
</script>

<template>
  <n-config-provider>
    <n-global-style />
    <n-message-provider>
      <router-view />
    </n-message-provider>
  </n-config-provider>
</template>
