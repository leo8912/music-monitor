/**
 * 用户/认证状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import * as authApi from '@/api/auth'

export const useUserStore = defineStore('user', () => {
    // 状态
    const user = ref<User | null>(null)
    const isAuthenticated = ref(false)
    const authEnabled = ref(false)
    const isLoading = ref(false)

    // 计算属性
    const username = computed(() => user.value?.username || 'My Music')
    const avatar = computed(() => user.value?.avatar || '')

    // 方法
    const checkAuth = async () => {
        isLoading.value = true

        try {
            const result = await authApi.checkAuth()
            isAuthenticated.value = result.authenticated
            authEnabled.value = result.enabled

            if (result.user) {
                user.value = result.user
            }

            return result.authenticated
        } catch (error) {
            console.error('检查认证失败:', error)
            return false
        } finally {
            isLoading.value = false
        }
    }

    const login = async (username: string, password: string) => {
        isLoading.value = true

        try {
            const result = await authApi.login({ username, password })

            if (result.success) {
                isAuthenticated.value = true
                await fetchUser()
            }

            return result
        } catch (error: any) {
            return { success: false, message: error.message || '登录失败' }
        } finally {
            isLoading.value = false
        }
    }

    const logout = async () => {
        try {
            await authApi.logout()
        } catch {
            // 忽略错误
        } finally {
            user.value = null
            isAuthenticated.value = false
        }
    }

    const fetchUser = async () => {
        try {
            user.value = await authApi.getUser()
        } catch {
            // 忽略
        }
    }

    return {
        // 状态
        user,
        isAuthenticated,
        authEnabled,
        isLoading,

        // 计算属性
        username,
        avatar,

        // 方法
        checkAuth,
        login,
        logout,
        fetchUser
    }
})
