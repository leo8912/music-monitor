/**
 * 认证相关 API
 */

import { get, post } from './index'
import type { AuthState, LoginRequest, User } from '@/types'

// 检查认证状态
export const checkAuth = (): Promise<AuthState> => {
    return get('/api/check_auth')
}

// 登录
export const login = (data: LoginRequest): Promise<{ success: boolean; message?: string }> => {
    return post('/api/login', data)
}

// 登出
export const logout = (): Promise<{ success: boolean }> => {
    return post('/api/logout')
}

// 获取用户信息
export const getUser = (): Promise<User> => {
    return get('/api/user')
}
