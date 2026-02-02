/**
 * 播放器相关类型定义
 */

import type { Song, MusicSource } from './song'

// 播放模式
export type PlayMode = 'sequence' | 'loop' | 'single' | 'random'

// 播放状态
export interface PlayerState {
    currentSong: Song | null
    playlist: Song[]
    playMode: PlayMode
    isPlaying: boolean
    isLoading: boolean
    currentTime: number
    duration: number
    volume: number
    isMuted: boolean
}

// 歌词行
export interface LyricLine {
    time: number
    text: string
}

// 当前播放信息（传递给播放器组件）
export interface PlayingInfo {
    title: string
    artist: string
    album: string
    cover?: string
    source: MusicSource
    mediaId: string
    localPath?: string
    isFavorite: boolean
}

// 频谱数据
export interface VisualizerData {
    frequencies: Uint8Array
    waveform: Uint8Array
}
