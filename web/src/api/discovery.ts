/**
 * 搜索相关 API
 */

import { get, instance } from './index'
import type { SearchSong, SearchArtist, SearchDownloadItem, ProbeQuality } from '@/types'

// 搜索歌曲
export const searchSongs = (params: {
    keyword: string
    limit?: number
}): Promise<SearchSong[]> => {
    return get('/api/discovery/search', {
        keyword: params.keyword,
        limit: params.limit || 20
    })
}

// 搜索歌手
export const searchArtists = (params: {
    keyword: string
    limit?: number
}): Promise<SearchArtist[]> => {
    return get('/api/discovery/search_artists', {
        keyword: params.keyword,
        limit: params.limit || 10
    })
}

// 搜索下载源 (GDStudio)
export async function searchDownload(params: {
    keyword: string
    limit?: number
}): Promise<SearchDownloadItem[]> {
    return get('/api/discovery/search_download', {
        keyword: params.keyword,
        limit: params.limit || 10
    })
}

export async function probeQualities(params: { source: string, id: string }): Promise<ProbeQuality[]> {
    return get('/api/discovery/probe_qualities', params)
}

// GDStudio API 接口有效性检查
export interface ApiHealthItem {
    source: string
    search_status: string      // ok / empty / unsupported / error
    search_count: number
    search_latency_ms: number
    url_status: string         // ok / empty / unsupported / error / skip
    url_latency_ms: number
    message: string
}

export interface ApiHealthResult {
    tested_at: string
    cached: boolean
    ttl_seconds: number
    total: number
    items: ApiHealthItem[]
}

export const getApiHealth = (refresh: boolean = false, source?: string): Promise<ApiHealthResult> => {
    const params: Record<string, any> = { refresh: refresh ? 1 : 0 }
    if (source) params.source = source
    return get('/api/discovery/api_health', params)
}

// 本地化歌手头像（后台触发，返回本地 /uploads/ 路径或空）
export const localizeArtistAvatar = (artistName: string): Promise<{ avatar: string }> => {
    return instance.post('/api/discovery/localize_artist_avatar', new URLSearchParams({
        artist_name: artistName
    }), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
}
