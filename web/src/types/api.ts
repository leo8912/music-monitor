/**
 * API 相关类型定义
 */

import type { LocalFile } from './song'

// 通用 API 响应
export interface ApiResponse<T = any> {
    success?: boolean
    message?: string
    data?: T
    error?: string
}

// 搜索下载项 (后端 SearchDownloadItemResponse: /api/discovery/search_download)
export interface SearchDownloadItem {
    id: string
    source: string
    title: string
    artist: string
    album?: string
    cover_url?: string
    quality?: number | null
    size?: number | null
    publish_time?: string
    // 前端局部 UI 状态 (非后端字段, 用于搜索页下载按钮 loading)
    _loading?: boolean
}

// 音质探测结果 (后端 ProbeQualityResponse: /api/discovery/probe_qualities)
export interface ProbeQuality {
    quality: number
    available: boolean
    actual_br?: number | null
    size?: number | null
}

// 移动端签名元数据 (后端 MobileMetadataResponse: /api/mobile/metadata)
export interface MobileMetadata {
    title?: string | null
    artist?: string | null
    album?: string | null
    cover?: string | null
    lyrics?: string | null
    audio_url?: string | null
    source?: string | null
    is_favorite?: boolean | null
    local_audio_path?: string | null
    id?: string | null
    unique_key?: string | null
}

// 后端歌曲原始返回 (snake_case 与前端 Song 兼容字段的并集)
// 用于 stores/组件把后端响应映射为前端 Song 时提供安全类型
export interface SongPayload {
    id: number
    title: string
    artist: string
    album?: string
    source?: string
    source_id?: string
    media_id?: string | number
    cover?: string
    pic_url?: string
    cover_url?: string
    local_path?: string
    local_audio_path?: string
    is_favorite?: boolean
    status?: string
    publish_time?: string
    created_at?: string
    found_at?: string
    played_at?: string
    available_sources?: string[]
    quality?: string
    quality_details?: string
    local_files?: LocalFile[]
}

// 下载进度通知 (WS / 轮询推送)
export interface DownloadStatusPayload {
    title: string
    artist: string
    message?: string
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

// 认证状态 (check_auth: user 为用户名字符串)
export interface AuthState {
    authenticated: boolean
    enabled: boolean
    user?: string | null
    avatar?: string | null
}

// 系统状态
export interface SystemStatus {
    status: string
    jobs: Array<{
        id: string
        next_run: string | null
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
    source_id: string
    status: string
    download_path?: string
    download_time?: string
    error_message?: string
    cover_url?: string
}

// 下载统计
export interface DownloadStats {
    total_downloads: number
    successful_downloads: number
    failed_downloads: number
    success_rate: number
}
