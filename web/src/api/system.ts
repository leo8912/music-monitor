/**
 * 系统配置相关 API
 */

import { get, post, patch } from './index'
import type { Settings, SystemStatus, DownloadHistory, DownloadStats, PaginatedResponse } from '@/types'

// 获取系统状态
export const getStatus = (): Promise<SystemStatus> => {
    return get('/api/status')
}

// 获取设置
export const getSettings = (): Promise<Settings> => {
    return get('/api/settings')
}

// 保存设置
export const saveSettings = (data: Partial<Settings>): Promise<Settings> => {
    return patch('/api/settings', data)
}

// 测试通知
export const testNotify = (type: string, config?: any): Promise<{ success: boolean; message: string }> => {
    return post('/api/settings/test-notify', { type, config })
}

// 检查通知状态
export const checkNotifyStatus = (channel: string): Promise<{ status: string; connected: boolean }> => {
    return get(`/api/check_notify_status/${channel}`)
}

// 获取下载历史
export const getDownloadHistory = (params: {
    skip?: number
    limit?: number
    source?: string
    status?: string
    artist?: string
}): Promise<PaginatedResponse<DownloadHistory>> => {
    return get('/api/download-history/', params)
}

// 获取下载统计
export const getDownloadStats = (): Promise<DownloadStats> => {
    return get('/api/download-history/stats')
}

// 重置数据库
export const resetDatabase = (): Promise<{ status: string; message: string }> => {
    return post('/api/system/reset_database')
}
