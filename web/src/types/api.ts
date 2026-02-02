/**
 * API 相关类型定义
 */

// 通用 API 响应
export interface ApiResponse<T = any> {
    success?: boolean
    message?: string
    data?: T
    error?: string
}

// 分页响应 (统一格式)
export interface PaginatedResponse<T> {
    items: T[]
    total: number
    page: number
    page_size: number
    total_pages: number
}

// 用户信息
export interface User {
    username: string
    avatar?: string
}

// 登录请求
export interface LoginRequest {
    username: string
    password: string
}

// 认证状态
export interface AuthState {
    authenticated: boolean
    enabled: boolean
    user?: User
}

// 系统状态
export interface SystemStatus {
    status: string
    jobs: Array<{
        id: string
        nextRun: string
    }>
}

// 设置配置
export interface Settings {
    global: {
        external_url: string
        check_interval_minutes: number
        theme: string
    }
    monitor: {
        netease: {
            enabled: boolean
            interval: number
            users: any[]
        }
        qqmusic: {
            enabled: boolean
            interval: number
            users: any[]
        }
    }
    download: {
        quality_preference: number
        sources: string[]
        max_concurrent_downloads: number
    }
    notify: {
        wecom?: WecomConfig
        telegram?: TelegramConfig
    }
    storage?: {
        favorites_dir: string
        cache_dir: string
    }
}

// 企业微信配置
export interface WecomConfig {
    corpid: string
    agentid: string
    corpsecret: string
    token?: string
    encoding_aes_key?: string
}

// Telegram 配置
export interface TelegramConfig {
    bot_token: string
    chat_id: string
}

// 下载历史记录
export interface DownloadHistory {
    id: number
    title: string
    artist: string
    album: string
    source: string
    sourceId: string
    status: string
    downloadPath?: string
    downloadTime?: string
    errorMessage?: string
    coverUrl?: string
}

// 下载统计
export interface DownloadStats {
    totalDownloads: number
    successfulDownloads: number
    failedDownloads: number
    successRate: number
}
