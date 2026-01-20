import { ref } from 'vue'

/**
 * 🎨 主题管理工具
 * 处理深色模式的应用、持久化和系统跟随
 */

// 全局响应式主题状态 ('light' 或 'dark')
export const themeMode = ref('light')     // 实际生效: 'light' | 'dark'
export const themePreference = ref('auto') // 用户偏好: 'light' | 'dark' | 'auto'

// 应用主题到 DOM 并更新状态
export const applyTheme = (theme) => {
    if (typeof document === 'undefined') return

    try {
        themePreference.value = theme // Update preference state

        const root = document.documentElement
        let effectiveTheme = theme

        if (theme === 'auto') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
            effectiveTheme = prefersDark ? 'dark' : 'light'
        }

        themeMode.value = effectiveTheme
        root.setAttribute('data-theme', effectiveTheme)
    } catch (e) {
        console.warn('主题应用失败:', e)
    }
}

// 初始化主题（从本地存储读取）
export const initTheme = () => {
    if (typeof window === 'undefined') return
    const saved = localStorage.getItem('user_theme_pref') || 'auto'
    console.log('🎨 初始化主题:', saved)
    applyTheme(saved)

    // 监听系统主题变化 (仅当设置为 auto 时生效)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        const savedNow = localStorage.getItem('user_theme_pref') || 'auto'
        if (savedNow === 'auto') {
            applyTheme('auto')
        }
    })
}

// 保存主题设置
export const saveTheme = (theme) => {
    localStorage.setItem('user_theme_pref', theme)
    applyTheme(theme)
}
