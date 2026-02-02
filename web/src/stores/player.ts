/**
 * 播放器状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed, nextTick } from 'vue'
import type { Song, PlayMode, LyricLine } from '@/types'
import * as playerApi from '@/api/player'

import { useLibraryStore, usePlayerStore as useSelfStore } from '@/stores'

export const usePlayerStore = defineStore('player', () => {
    // [New] Lazy load library store to avoid circular dependency
    let libraryStore: any = null
    const getLibraryStore = () => {
        if (!libraryStore) libraryStore = useLibraryStore()
        return libraryStore
    }
    // 状态
    const currentSong = ref<Song | null>(null)
    const playlist = ref<Song[]>([])
    const playMode = ref<PlayMode>('sequence')
    const isPlaying = ref(false)
    const isLoading = ref(false)
    const currentTime = ref(0)
    const duration = ref(0)
    const volume = ref(80)
    const isMuted = ref(false)
    const audioUrl = ref('')
    const lyrics = ref<LyricLine[]>([])
    const currentLyricIndex = ref(-1)
    const showLyricsPanel = ref(false)
    const downloadMessage = ref('')

    // 计算属性
    const progress = computed(() => {
        if (duration.value === 0) return 0
        return (currentTime.value / duration.value) * 100
    })

    const hasNext = computed(() => {
        if (playlist.value.length === 0) return false
        const idx = playlist.value.findIndex(s => s.id === currentSong.value?.id)
        return idx < playlist.value.length - 1
    })

    const hasPrev = computed(() => {
        if (playlist.value.length === 0) return false
        const idx = playlist.value.findIndex(s => s.id === currentSong.value?.id)
        return idx > 0
    })

    // 方法
    const playSong = async (song: Song) => {
        // [Fix] Reset state immediately and wait for next tick to ensure watchers (e.g. in BottomPlayer) trigger
        isPlaying.value = false
        audioUrl.value = ''
        await nextTick()

        isLoading.value = true
        currentSong.value = song

        try {
            // 如果有本地路径，直接播放
            if (song.localPath) {
                // [Fix] 同时支持正斜杠和反斜杠提取文件名
                const parts = song.localPath.split(/[/\\]/)
                const filename = parts.pop()
                if (filename) {
                    audioUrl.value = playerApi.getAudioUrl(filename)
                    console.log(`[Player] Playing local file: ${filename}`)
                }
            } else {
                // 触发下载
                const result = await playerApi.downloadAudio({
                    title: song.title,
                    artist: song.artist,
                    album: song.album,
                    source: song.source,
                    songId: song.sourceId
                })

                if (result.localPath) {
                    const filename = result.localPath.split('/').pop() || result.localPath.split('\\').pop()
                    if (filename) {
                        audioUrl.value = playerApi.getAudioUrl(filename)
                        song.localPath = result.localPath
                    }
                } else {
                    throw new Error('下载未返回有效路径')
                }
            }

            if (!audioUrl.value) {
                throw new Error('音频地址无效')
            }

            // [New] Universal Quality Inference logic
            // Runs for both local-cached and newly-downloaded songs
            if (!song.quality && song.localPath) {
                const ext = song.localPath.split('.').pop()?.toLowerCase()
                if (ext === 'flac' || ext === 'wav' || ext === 'ape') song.quality = 'SQ'
                else if (ext === 'mp3') song.quality = 'HQ'
            }

            // 获取歌词 - [Non-blocking] Move after audioUrl is set
            console.log('[Player] About to fetch lyrics (non-blocking) for:', song.title, song.artist)
            fetchLyrics(song.title, song.artist, song.id.toString())

            isPlaying.value = true

            // 上报播放记录 (异步)
            playerApi.recordPlay({
                title: song.title,
                artist: song.artist,
                album: song.album,
                source: song.source,
                media_id: song.sourceId || song.id.toString(),
                cover: song.cover
            }).catch(e => console.warn('记录播放历史失败:', e))

            // [Modified] Do NOT re-fetch library on every play.
            // Only fetch if explicitly needed (e.g. after download completes in background, but that's handled by notification/refresh button)
            // The previous logic caused the list to reset/jump which annoyed the user.
        } catch (error) {
            console.error('播放失败:', error)
            isPlaying.value = false
            currentSong.value = null
        } finally {
            isLoading.value = false
            if (audioUrl.value) downloadMessage.value = ''
        }
    }

    const updateDownloadStatus = (data: any) => {
        // Only update if it's the current song
        if (currentSong.value &&
            currentSong.value.title === data.title &&
            currentSong.value.artist === data.artist) {
            downloadMessage.value = data.message

            // If download complete is implied by message (backend sends "✅ 下载完成！")
            // it doesn't hurt to wait for play() to finalize.
            // But if we want to be proactive, we can.
        }
    }

    const fetchLyrics = async (title: string, artist: string, songId?: string) => {
        console.log('[Player] fetchLyrics called with:', { title, artist, songId })
        try {
            const result = await playerApi.getLyrics({ title, artist, song_id: songId })
            console.log('[Player] API response:', result)
            if (result.success && result.lyrics) {
                lyrics.value = parseLrc(result.lyrics)
            } else {
                lyrics.value = []
            }
        } catch (error) {
            console.error('[Player] Failed to fetch lyrics:', error)
            lyrics.value = []
        }
    }

    const parseLrc = (lrcText: string): LyricLine[] => {
        const lines: LyricLine[] = []
        const regex = /\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)/g
        let match

        while ((match = regex.exec(lrcText)) !== null) {
            const min = parseInt(match[1])
            const sec = parseInt(match[2])
            const ms = parseInt(match[3])
            const time = min * 60 + sec + ms / (match[3].length === 2 ? 100 : 1000)
            const text = match[4].trim()
            if (text) {
                lines.push({ time, text })
            }
        }

        return lines.sort((a, b) => a.time - b.time)
    }

    const playNext = () => {
        if (!hasNext.value) return

        const idx = playlist.value.findIndex(s => s.id === currentSong.value?.id)
        if (idx >= 0 && idx < playlist.value.length - 1) {
            playSong(playlist.value[idx + 1])
        }
    }

    const playPrev = () => {
        if (!hasPrev.value) return

        const idx = playlist.value.findIndex(s => s.id === currentSong.value?.id)
        if (idx > 0) {
            playSong(playlist.value[idx - 1])
        }
    }

    const togglePlay = () => {
        isPlaying.value = !isPlaying.value
    }

    const setVolume = (val: number) => {
        volume.value = val
        isMuted.value = val === 0
    }

    const toggleMute = () => {
        isMuted.value = !isMuted.value
    }

    const toggleLyricsPanel = () => {
        showLyricsPanel.value = !showLyricsPanel.value
    }

    const updateTime = (time: number) => {
        currentTime.value = time

        // 更新歌词索引
        if (lyrics.value.length > 0) {
            for (let i = lyrics.value.length - 1; i >= 0; i--) {
                if (time >= lyrics.value[i].time) {
                    currentLyricIndex.value = i
                    break
                }
            }
        }
    }

    const setDuration = (dur: number) => {
        duration.value = dur
    }

    const setPlaylist = (songs: Song[]) => {
        playlist.value = songs
    }

    const seekTo = (percent: number) => {
        if (duration.value > 0) {
            currentTime.value = (percent / 100) * duration.value
        }
    }

    const seek = (time: number) => {
        if (duration.value > 0) {
            currentTime.value = time
        }
    }

    const clearPlayer = () => {
        currentSong.value = null
        audioUrl.value = ''
        isPlaying.value = false
        currentTime.value = 0
        duration.value = 0
        lyrics.value = []
        currentLyricIndex.value = -1
    }

    return {
        // 状态
        currentSong,
        playlist,
        playMode,
        isPlaying,
        isLoading,
        currentTime,
        duration,
        volume,
        isMuted,
        audioUrl,
        lyrics,
        currentLyricIndex,
        showLyricsPanel,
        downloadMessage,

        // 计算属性
        progress,
        hasNext,
        hasPrev,

        // 方法
        playSong,
        playNext,
        playPrev,
        togglePlay,
        setVolume,
        toggleMute,
        toggleLyricsPanel,
        updateDownloadStatus,
        updateTime,
        setDuration,
        setPlaylist,
        seekTo,
        seek,
        clearPlayer
    }
})
