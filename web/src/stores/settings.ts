/**
 * 设置/主题状态管理
 */

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { Settings, SystemStatus } from '@/types'
import { useLocalStorage } from '@vueuse/core'

export const useSettingsStore = defineStore('settings', () => {
    // 状态
    const isDark = ref(false)
    const settings = ref<Settings | null>(null)
    const systemStatus = ref<SystemStatus | null>(null)
    const isLoading = ref(false)
    const themeStorage = useLocalStorage('theme', '')

    // 初始化主题
    const initTheme = () => {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches

        isDark.value = themeStorage.value ? themeStorage.value === 'dark' : prefersDark
        applyTheme()
    }

    const applyTheme = () => {
        document.documentElement.classList.toggle('dark', isDark.value)
    }

    const toggleTheme = () => {
        isDark.value = !isDark.value
        themeStorage.value = isDark.value ? 'dark' : 'light'
        applyTheme()
    }

    // 监听主题变化
    watch(isDark, applyTheme)

    // 获取设置
    const fetchSettings = async () => {
        isLoading.value = true

        try {
            settings.value = await systemApi.getSettings()
        } catch (error) {
            console.error('获取设置失败:', error)
        } finally {
            isLoading.value = false
        }
    }

    // 保存设置
    const saveSettings = async (newSettings: Settings) => {
        isLoading.value = true

        try {
            await systemApi.saveSettings(newSettings)
            settings.value = newSettings
            return true
        } catch (error) {
            console.error('保存设置失败:', error)
            return false
        } finally {
            isLoading.value = false
        }
    }

    // 获取系统状态
    const fetchStatus = async () => {
        try {
            systemStatus.value = await systemApi.getStatus()
        } catch (error) {
            console.error('获取状态失败:', error)
        }
    }

    // 触发检查
    const triggerCheck = async (source: string) => {
        try {
            const result = await systemApi.triggerCheck(source)
            return result
        } catch (error) {
            console.error('触发检查失败:', error)
            throw error
        }
    }

    // 触发扫描
    const triggerScan = async () => {
        try {
            const result = await systemApi.triggerScan()
            return result
        } catch (error) {
            console.error('触发扫描失败:', error)
            throw error
        }
    }

    return {
        // 状态
        isDark,
        settings,
        systemStatus,
        isLoading,

        // 方法
        initTheme,
        toggleTheme,
        fetchSettings,
        saveSettings,
        fetchStatus,
        triggerCheck,
        triggerScan
    }
})
