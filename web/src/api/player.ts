/**
 * 播放/下载相关 API
 */

import { get, post } from './index'
import type { DownloadRequest, DownloadResult, LyricLine } from '@/types'

// 下载音频
export const downloadAudio = (data: DownloadRequest): Promise<DownloadResult> => {
    return post('/api/download_audio', {
        title: data.title,
        artist: data.artist,
        album: data.album,
        source: data.source,
        song_id: data.songId,
        pic_url: data.picUrl
    })
}

// 获取音频 URL（流式播放）
export const getAudioUrl = (filename: string): string => {
    return `/api/audio/${encodeURIComponent(filename)}`
}

// 获取播放链接（在线）
export const getPlayUrl = (source: string, id: string): string => {
    return `/api/play/${source}/${id}`
}

// 获取歌词
export const getLyrics = (params: {
    title: string
    artist: string
    song_id?: string
}): Promise<{ success: boolean; lyrics?: string }> => {
    return get('/api/metadata/lyrics', {
        title: params.title,
        artist: params.artist,
        song_id: params.song_id
    })
}

// 获取封面
export const getCoverUrl = (params: {
    title: string
    artist: string
}): string => {
    return `/api/metadata/cover?title=${encodeURIComponent(params.title)}&artist=${encodeURIComponent(params.artist)}`
}

// 获取移动端元数据
export const getMobileMetadata = (params: {
    id: string
    sign: string
    expires: string
}): Promise<{
    title: string
    artist: string
    album: string
    cover?: string
    lyrics?: string
    audio_url: string
    source: string
    is_favorite: boolean
}> => {
    return get('/api/mobile/metadata', params)
}

// 记录播放历史
export const recordPlay = (data: {
    title: string
    artist: string
    album: string
    source: string
    media_id: string
    cover?: string
}): Promise<{ success: boolean }> => {
    return post('/api/history/record', data)
}
