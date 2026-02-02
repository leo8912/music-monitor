/**
 * 歌手相关类型定义
 */

import type { MusicSource } from './song'

// 歌手基础信息
export interface Artist {
    id: string
    name: string
    source: MusicSource // "database"
    sources?: MusicSource[] // Linked sources
    avatar?: string
    songCount?: number
    song_count?: number // 兼容旧版
    availableSources?: string[]
    is_monitored?: boolean
    isMonitored?: boolean
}

// 合并后的歌手（跨平台）
export interface MergedArtist {
    name: string
    avatar?: string
    sources: MusicSource[]
    ids: Array<{ source: MusicSource; id: string }>
    songCount?: number
}

// 搜索结果中的歌手
export interface SearchArtist {
    id: string
    name: string
    source: MusicSource
    avatar?: string
    neteaseId?: string
    qqmusicId?: string
}

// 添加歌手请求
export interface AddArtistRequest {
    name: string
    source?: MusicSource
    id?: string
    avatar?: string
}
