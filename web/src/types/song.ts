/**
 * 歌曲相关类型定义
 */

// 歌曲来源平台
export type MusicSource = 'netease' | 'qqmusic' | 'kuwo' | 'kugou' | 'migu' | 'local' | 'database'

// 歌曲基础信息
export interface Song {
    id: number
    title: string
    artist: string
    album: string
    source: MusicSource
    sourceId: string
    cover?: string
    duration?: number
    localPath?: string
    isFavorite: boolean
    status: SongStatus
    publishTime?: string
    createdAt?: string
    foundAt?: string
    availableSources?: string[]
    quality?: string // SQ, HQ, Hi-Res
}

// 歌曲状态
export type SongStatus = 'PENDING' | 'PENDING_METADATA' | 'DOWNLOADED' | 'FAILED'

// 搜索结果中的歌曲
export interface SearchSong {
    id: string
    title: string
    artist: string | string[]
    album: string
    source: MusicSource
    cover?: string
    picId?: string
}

// 歌曲列表响应
export interface SongListResponse {
    items: Song[]
    total: number
    skip: number
    limit: number
}

// 下载请求
export interface DownloadRequest {
    title: string
    artist: string
    album: string
    source: MusicSource
    songId: string
    picUrl?: string
}

// 下载结果
export interface DownloadResult {
    localPath: string
    quality: number
    hasLyric: boolean
}
