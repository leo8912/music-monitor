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

            // check_auth 的 user 字段是用户名（字符串），完整用户信息由 /api/user 提供
            if (result.authenticated) {
                await fetchUser()
            } else {
                user.value = null
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
        } catch (error) {
            const msg = error instanceof Error ? error.message : '登录失败'
            return { success: false, message: msg }
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
