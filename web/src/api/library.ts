/**
 * 资料库相关 API
 */

import { get, post, del } from './index'
import type { Song, SongListResponse, Artist } from '@/types'

// 获取歌曲列表
export const getSongs = (params: {
    page?: number
    page_size?: number
    artistName?: string
    isFavorite?: boolean
    sortBy?: string
    order?: 'asc' | 'desc'
}): Promise<SongListResponse> => {
    return get('/api/library/songs', {
        page: params.page,
        page_size: params.page_size,
        artist_name: params.artistName,
        is_favorite: params.isFavorite,
        sort_by: params.sortBy,
        order: params.order
    })
}

// 获取纯本地歌曲 (独立接口)
export const getLocalSongs = (params: {
    page?: number
    page_size?: number
}): Promise<SongListResponse> => {
    return get('/api/library/local-songs', params)
}

// 获取历史记录（带去重）
export const getHistory = (params: {
    page?: number
    page_size?: number
    author?: string
    downloadedOnly?: boolean
}): Promise<{ items: Song[]; total: number; page: number; page_size: number; total_pages: number }> => {
    return get('/api/history', {
        page: params.page,
        page_size: params.page_size,
        author: params.author,
        downloaded_only: params.downloadedOnly
    })
}

// 获取歌手列表
export const getArtists = (): Promise<Artist[]> => {
    return get('/api/subscription/artists')
}

// 添加歌手
export const addArtist = (data: {
    name: string
    source: string
    id: string
    avatar?: string
}): Promise<{ success: boolean; message: string }> => {
    // Map 'id' (source id) to backend 'artist_id'
    return post('/api/subscription/artists', {
        name: data.name,
        source: data.source,
        artist_id: data.id,
        avatar: data.avatar
    })
}

// 删除歌手 (by DB ID)
export const deleteArtist = (id: number): Promise<{ success: boolean; message: string }> => {
    return del(`/api/subscription/artists/${id}`)
}

// 切换收藏
export const toggleFavorite = (songId: number): Promise<{ song_id: number; is_favorite: boolean }> => {
    return post(`/api/library/songs/${songId}/favorite`)
}

// 删除歌曲
export const deleteSong = (songId: number): Promise<{ success: boolean }> => {
    return del(`/api/library/songs/${songId}`)
}

// 刷新歌手
export const refreshArtist = (artistName: string): Promise<{ success: boolean; new_songs_count: number }> => {
    return post('/api/library/refresh_artist', { artist_name: artistName })
}

// 扫描本地文件
export const scanLibrary = (): Promise<{ success: boolean; new_files_found: number; removed_files_count: number }> => {
    return post('/api/library/scan')
}

// 补全本地文件标签
export const enrichLocalFiles = (limit?: number): Promise<{ success: boolean; enriched_count: number }> => {
    const url = limit ? `/api/library/local/enrich?limit=${limit}` : '/api/library/local/enrich'
    return post(url)
}

// 刷新资料库元数据
export const refreshLibraryMetadata = (limit?: number): Promise<{ success: boolean; enriched_count: number }> => {
    const url = limit ? `/api/library/metadata/refresh?limit=${limit}` : '/api/library/metadata/refresh'
    return post(url)
}

// 手动匹配元数据
export const matchMetadata = (data: { song_id: number, target_source: string, target_song_id: string }): Promise<{ success: boolean }> => {
    return post('/api/library/match-metadata', data)
}

// 重新下载歌曲
export const redownloadSong = (data: {
    song_id: number,
    source: string,
    track_id: string,
    quality?: number,
    title?: string,
    artist?: string
}): Promise<{ success: boolean, song?: any }> => {
    return post('/api/library/redownload', data)
}

// 直接下载 (从搜索结果)
export const downloadSong = (data: {
    title: string
    artist: string
    album: string
    source: string
    source_id: string
    quality?: number
    cover_url?: string
}): Promise<{ success: boolean; song?: any }> => {
    return post('/api/library/download', data)
}
