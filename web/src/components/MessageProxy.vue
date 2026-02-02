<script setup lang="ts">
import { useMessage } from 'naive-ui'

// Expose message API to window for usage in stores/outside components
// @ts-ignore
window.$message = useMessage()
</script>

<template>
  <!-- Proxy component, renders nothing -->
</template>
