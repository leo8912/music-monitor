/**
 * 歌曲相关类型定义
 */

// 歌曲来源平台
export type MusicSource = 'netease' | 'qqmusic' | 'kuwo' | 'kugou' | 'migu' | 'local' | 'database'

// 本地文件详情 (Song.local_files 元素, 对应后端 Song.local_files property)
export interface LocalFile {
    id: number
    source_id?: string
    path: string
    quality: string // 'PQ' | 'HQ' | 'SQ' | ...
    format: string  // 'MP3' | 'FLAC' | 'UNK' | ...
}

// 歌曲基础信息
export interface Song {
    id: number
    title: string
    artist: string
    album: string
    source: MusicSource
    source_id: string
    cover?: string
    duration?: number
    local_path?: string
    is_favorite: boolean
    status: SongStatus
    publish_time?: string
    created_at?: string
    found_at?: string
    played_at?: string // 播放/浏览时间 (历史页)
    available_sources?: string[]
    quality?: string // SQ, HQ, Hi-Res
    quality_details?: string
    local_files?: LocalFile[]
}

// 歌曲状态
export type SongStatus = 'PENDING' | 'PENDING_METADATA' | 'DOWNLOADED' | 'FAILED'

// 搜索结果中的歌曲 (后端 SongInfoResponse: cover_url 而非 cover)
export interface SearchSong {
    id: string
    title: string
    artist: string
    album: string
    source: MusicSource
    cover?: string
    cover_url?: string
    duration?: number
    publish_time?: string
    picId?: string
    // 部分搜索场景 (GDStudio 下载检索) 会附带音质/大小信息
    quality?: number | null
}

// 歌曲列表响应 (统一分页: page + page_size)
export interface SongListResponse {
    items: Song[]
    total: number
    page: number
    page_size: number
    total_pages: number
}

// 下载请求
// 播放器侧下载 (POST /api/download_audio)
export interface DownloadRequest {
    title: string
    artist: string
    album: string
    source: MusicSource
    songId: string
    picUrl?: string
}

// 直接下载请求 (搜索结果 → POST /api/library/download)
export interface DirectDownloadRequest {
    title: string
    artist: string
    album: string
    source: string
    source_id: string
    quality?: number
    cover_url?: string
}

// 下载结果
export interface DownloadResult {
    local_path: string
    quality: number
    has_lyric: boolean
    song_id?: string | number
}
