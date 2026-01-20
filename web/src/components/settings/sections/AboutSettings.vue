<script setup>
/**
 * ℹ️ 关于面板
 */
import { ref, onMounted } from 'vue'
import { NIcon, NButton } from 'naive-ui'
import { LogoGithub, DocumentTextOutline, BugOutline } from '@vicons/ionicons5'
import axios from 'axios'

// 应用信息
const appInfo = ref({
    name: 'Music Monitor',
    frontendVersion: '加载中...',
    backendVersion: '加载中...',
    buildDate: '加载中...',
    author: 'Leo',
    github: 'https://github.com/leo8912/music-monitor'
})

// 从API获取版本信息
onMounted(async () => {
    try {
        const response = await axios.get('/api/version')
        if (response.data) {
            appInfo.value = {
                ...appInfo.value,
                frontendVersion: response.data.frontend_version,
                backendVersion: response.data.backend_version,
                buildDate: response.data.build_date,
                name: response.data.name,
                author: response.data.author
            }
        }
    } catch (error) {
        console.error('Failed to fetch version info:', error)
        // 保持默认值
    }
})
</script>

<template>
    <div class="settings-section about-section">
        <div class="app-logo">
            <span class="logo-icon">🎵</span>
        </div>
        
        <h1 class="app-name">{{ appInfo.name }}</h1>
        <div class="version-info">
            <p class="app-version">前端版本 v{{ appInfo.frontendVersion }}</p>
            <p class="app-version">后端版本 v{{ appInfo.backendVersion }}</p>
        </div>
        <p class="app-build">构建于 {{ appInfo.buildDate }}</p>
        
        <div class="about-actions">
            <n-button quaternary size="small" tag="a" :href="appInfo.github" target="_blank">
                <template #icon><n-icon><LogoGithub /></n-icon></template>
                GitHub
            </n-button>
            <n-button quaternary size="small">
                <template #icon><n-icon><DocumentTextOutline /></n-icon></template>
                文档
            </n-button>
            <n-button quaternary size="small">
                <template #icon><n-icon><BugOutline /></n-icon></template>
                反馈
            </n-button>
        </div>
        
        <div class="about-credits">
            <p>Made with ❤️ by {{ appInfo.author }}</p>
            <p class="license">开源协议: MIT License</p>
        </div>
    </div>
</template>

<style scoped>
.about-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px 24px;
    text-align: center;
    min-height: 100%;
}

.app-logo {
    width: 80px;
    height: 80px;
    background: linear-gradient(135deg, #FA233B, #FF6B8A);
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
    box-shadow: 0 8px 24px rgba(250, 35, 59, 0.3);
}

.logo-icon {
    font-size: 40px;
    filter: grayscale(1) brightness(100);
}

.app-name {
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary, #1d1d1f);
    margin: 0 0 12px;
}

.version-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 8px;
}

.app-version {
    font-size: 15px;
    color: var(--text-secondary, #86868b);
    margin: 0;
}

.app-build {
    font-size: 13px;
    color: var(--text-tertiary, #aeaeb2);
    margin: 0 0 24px;
}

.about-actions {
    display: flex;
    gap: 8px;
    margin-bottom: 32px;
}

.about-credits {
    font-size: 12px;
    color: var(--text-secondary, #86868b);
}

.about-credits p {
    margin: 4px 0;
}

.license {
    color: var(--text-tertiary, #aeaeb2);
}

/* 深色模式 */
:root[data-theme="dark"] .app-name {
    color: #f5f5f7;
}
</style>
