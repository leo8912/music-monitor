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
    storage: {
        library_dir: string
        cache_dir: string
        favorites_dir: string
        max_cache_size: number
        cleanup_threshold: number
    }
    database: {
        url: string
        echo: boolean
        pool_size: number
        max_overflow: number
    }
    logging: {
        level: string
        format: string
        file: string
        max_bytes: number
        backup_count: number
    }
    system: {
        external_url: string
    }
    auth: {
        enabled: boolean
        secret_key: string
        algorithm: string
        access_token_expire_minutes: number
        refresh_token_expire_days: number
        username?: string
        password?: string
    }
    api: {
        rate_limit: { requests_per_minute: number; burst_size: number }
        timeout: number
    }
    download: {
        max_concurrent_downloads: number
        timeout: number
        retry_attempts: number
        quality_preference: number
        sources: string[]
    }
    monitor: {
        enabled: boolean
        interval: number
    }
    metadata: {
        enable_lyrics: boolean
        enable_cover: boolean
        enable_album: boolean
        lyrics_priority: string[]
        cover_priority: string[]
        album_priority: string[]
    }
    scheduler: {
        check_interval_minutes: number
        sync_interval_hours: number
        cleanup_interval_hours: number
    }
    notify: {
        enabled: boolean
        wecom: WecomConfig
        telegram: TelegramConfig
    }
}

// 企业微信配置
export interface WecomConfig {
    enabled: boolean
    corp_id: string
    agent_id: string
    secret: string
    token?: string
    encoding_aes_key?: string
}

// Telegram 配置
export interface TelegramConfig {
    enabled: boolean
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
