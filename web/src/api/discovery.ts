/**
 * 搜索相关 API
 */

import { get } from './index'
import type { SearchSong, SearchArtist } from '@/types'

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
}): Promise<any[]> {
    return get('/api/discovery/search_download', {
        keyword: params.keyword,
        limit: params.limit || 10
    })
}

export async function probeQualities(params: { source: string, id: string }): Promise<any[]> {
    return get('/api/discovery/probe_qualities', params)
}
