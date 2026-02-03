/**
 * 资料库状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Song, Artist, MergedArtist, MusicSource } from '@/types'
import * as libraryApi from '@/api/library'

export const useLibraryStore = defineStore('library', () => {
    // 状态
    const songs = ref<Song[]>([])
    const artists = ref<Artist[]>([])
    const selectedArtistName = ref<string | null>(null)
    const totalSongs = ref(0)
    const historySongs = ref<Song[]>([])
    const totalHistorySongs = ref(0)
    const currentPage = ref(1)
    const currentHistoryPage = ref(1)
    const pageSize = ref(20)
    const isLoading = ref(false)
    const refreshingArtistName = ref<string | null>(null)
    const sortField = ref('publish_time')
    const sortOrder = ref<'asc' | 'desc'>('desc')

    // 计算属性 - 合并同名歌手
    const mergedArtists = computed<MergedArtist[]>(() => {
        const map = new Map<string, MergedArtist>()

        artists.value.forEach(a => {
            if (!map.has(a.name)) {
                // Merge sources: prefer availableSources from backend, fallback to sources array or single source
                const sourceList = (a.availableSources || a.sources || (a.source === 'database' ? [] : [a.source])) as MusicSource[]

                const idEntry = { source: a.source, id: a.id }

                map.set(a.name, {
                    name: a.name,
                    avatar: a.avatar,
                    sources: sourceList,
                    ids: [idEntry],
                    songCount: a.songCount || 0
                })
            }
            // Since backend is now normalized, duplicates by name shouldn't happen for Monitored Artists.
            // But if we had mixed sources... 
            // We assume backend handles uniqueness.    
        })

        return Array.from(map.values())
    })

    const selectedArtist = computed(() => {
        if (!selectedArtistName.value) return null
        return mergedArtists.value.find(a => a.name === selectedArtistName.value) || null
    })

    // 方法
    const fetchSongs = async (page = 1) => {
        isLoading.value = true
        currentPage.value = page

        try {
            const result = await libraryApi.getSongs({
                page: page,
                page_size: pageSize.value,
                artistName: selectedArtistName.value || undefined,
                isFavorite: undefined,
                sortBy: sortField.value,
                order: sortOrder.value
            })

            // 转换为 Song 类型
            // result is SongListResponse which has 'items'
            // @ts-ignore
            const items = result.items || result.songs || []
            songs.value = items.map((s: any) => ({
                id: s.id,
                title: s.title,
                artist: s.artist,
                album: s.album || '',
                source: s.source || 'local',
                source_id: s.source_id || s.media_id || s.id,
                cover: s.cover || s.cover_url || s.pic_url,
                local_path: s.local_path || s.local_audio_path || s.localPath,
                is_favorite: s.is_favorite || false,
                status: s.status || 'DOWNLOADED',
                publish_time: s.publish_time || s.publishTime,
                created_at: s.created_at || s.createdAt,
                found_at: s.found_at || s.foundAt,
                available_sources: s.available_sources || s.availableSources || [],
                quality: s.quality,
                local_files: s.local_files || s.localFiles || []
            }))

            totalSongs.value = result.total
        } catch (error) {
            console.error('获取歌曲失败:', error)
        } finally {
            isLoading.value = false
        }
    }

    const fetchArtists = async () => {
        try {
            const result = await libraryApi.getArtists()
            artists.value = result
        } catch (error) {
            console.error('获取歌手失败:', error)
        }
    }

    const fetchLocalSongs = async (page = 1) => {
        isLoading.value = true
        currentPage.value = page
        try {
            const result = await libraryApi.getLocalSongs({
                page: page,
                page_size: pageSize.value,
                sortBy: sortField.value,
                order: sortOrder.value
            })

            // @ts-ignore
            const items = result.items || []
            songs.value = items.map((s: any) => ({
                id: s.id,
                title: s.title,
                artist: s.artist,
                album: s.album || '',
                source: s.source || 'local',
                source_id: s.source_id,
                cover: s.cover || s.pic_url,
                local_path: s.local_path,
                is_favorite: s.is_favorite || false,
                status: s.status,
                publish_time: s.publish_time || s.publishTime,
                created_at: s.created_at || s.createdAt,
                available_sources: s.available_sources || s.availableSources || [],
                quality: s.quality,
                local_files: s.local_files || s.localFiles || []
            }))
            totalSongs.value = result.total
        } catch (error) {
            console.error('获取本地音乐失败:', error)
        } finally {
            isLoading.value = false
        }
    }

    const fetchHistory = async (page = 1) => {
        isLoading.value = true
        currentHistoryPage.value = page
        try {
            const result = await libraryApi.getHistory({
                page: page,
                page_size: pageSize.value,
                sortBy: sortField.value,
                order: sortOrder.value
            })

            // @ts-ignore
            const items = result.items || []
            historySongs.value = items.map((s: any) => ({
                id: s.id || s.media_id,
                title: s.title,
                artist: s.artist,
                album: s.album || '',
                source: s.source || 'local',
                source_id: s.source_id || s.media_id,
                cover: s.cover || s.cover_url || s.pic_url,
                local_path: s.local_path || s.local_audio_path || s.localPath,
                is_favorite: s.is_favorite || false,
                status: s.status || 'DOWNLOADED',
                publish_time: s.publish_time || s.publishTime,
                created_at: s.created_at || s.createdAt,
                found_at: s.found_at || s.foundAt,
                available_sources: s.available_sources || s.availableSources || [],
                quality: s.quality
            }))
            totalHistorySongs.value = result.total
        } catch (error) {
            console.error('获取历史记录失败:', error)
        } finally {
            isLoading.value = false
        }
    }

    const selectArtist = (artist: MergedArtist | null) => {
        selectedArtistName.value = artist?.name || null
        fetchSongs(1)
    }

    const addArtist = async (name: string, source: string, id: string, avatar?: string) => {
        try {
            // Note: id passed here is SOURCE_ID (e.g. mid_123)
            await libraryApi.addArtist({ name, source, id, avatar })
            await fetchArtists()
            return true
        } catch (error) {
            console.error('添加歌手失败:', error)
            return false
        }
    }

    const deleteSong = async (song: Song) => {
        try {
            await libraryApi.deleteSong(song.id)
            // Remove from local list
            const index = songs.value.findIndex(s => s.id === song.id)
            if (index !== -1) {
                songs.value.splice(index, 1)
                totalSongs.value--
            }
            return true
        } catch (error) {
            console.error('删除歌曲失败:', error)
            return false
        }
    }

    const deleteArtist = async (artist: MergedArtist) => {
        try {
            // New Logic: Delete by Logical ID
            // We look for the entry corresponding to the logical artist
            const logicalIdEntry = artist.ids.find(x => x.source === 'database' || !x.source) || artist.ids[0]

            if (logicalIdEntry) {
                // Convert ID to number (backend expects int)
                // Wait, artist.id is string in frontend types usually?
                // In SubscriptionService, we return id: str(a.id)
                const idInt = parseInt(logicalIdEntry.id)
                if (!isNaN(idInt)) {
                    await libraryApi.deleteArtist(idInt)
                }
            }

            await fetchArtists()

            // If deleting the currently selected artist, clear selection
            if (selectedArtistName.value === artist.name) {
                selectedArtistName.value = null
            }

            // Always refresh song list to remove deleted songs
            await fetchSongs(1)

            return true
        } catch (error) {
            console.error('删除歌手失败:', error)
            return false
        }
    }

    const toggleFavorite = async (song: Song) => {
        try {
            const result = await libraryApi.toggleFavorite(song.id)
            song.is_favorite = result.is_favorite
            return true
        } catch (error) {
            console.error('切换收藏失败:', error)
            return false
        }
    }

    const refresh = async () => {
        await Promise.all([
            fetchArtists(),
            fetchSongs(currentPage.value)
        ])
    }

    const repairSong = async (song: Song) => {
        try {
            isLoading.value = true
            console.log('Repairing song:', song)
            await refresh()
            return true
        } catch (error) {
            console.error('修复歌曲失败:', error)
            return false
        }
    }

    const refreshArtist = async (artist: MergedArtist) => {
        refreshingArtistName.value = artist.name
        try {
            console.log('Refreshing artist:', artist.name)
            await libraryApi.refreshArtist(artist.name)
            await fetchSongs(currentPage.value)
            return true
        } catch (error) {
            console.error('刷新歌手失败:', error)
            return false
        } finally {
            refreshingArtistName.value = null
        }
    }

    const updateSongInList = (updatedData: any) => {
        const index = songs.value.findIndex(s => s.id === updatedData.id)
        if (index !== -1) {
            // Map backend fields to frontend fields
            const mappedSong: Song = {
                id: updatedData.id,
                title: updatedData.title,
                artist: updatedData.artist,
                album: updatedData.album || '',
                source: updatedData.source || 'local',
                source_id: updatedData.source_id || updatedData.media_id || updatedData.id,
                cover: updatedData.cover || updatedData.pic_url,
                local_path: updatedData.local_path || updatedData.local_audio_path,
                is_favorite: updatedData.is_favorite || false,
                status: updatedData.status || 'DOWNLOADED',
                publish_time: updatedData.publish_time,
                created_at: updatedData.created_at,
                found_at: updatedData.found_at,
                available_sources: updatedData.available_sources || [],
                quality: updatedData.quality,
                local_files: updatedData.local_files || updatedData.localFiles || []
            }
            songs.value[index] = mappedSong
            return mappedSong
        }
        return null
    }

    return {
        // 状态
        songs,
        artists,
        selectedArtistName,
        totalSongs,
        currentPage,
        pageSize,
        isLoading,
        refreshingArtistName,
        historySongs,
        totalHistorySongs,
        currentHistoryPage,

        // 计算属性
        mergedArtists,
        selectedArtist,

        // 方法
        fetchSongs,
        fetchHistory,
        fetchArtists,
        selectArtist,
        addArtist,
        deleteArtist,
        toggleFavorite,
        refresh,
        repairSong,
        refreshArtist,
        downloadSong: async (data: any) => {
            try {
                const res = await libraryApi.downloadSong(data)
                if (res.success && res.song) {
                    await fetchSongs(1) // Refresh list to show new song
                    return true
                }
                return false
            } catch (e) {
                console.error("Download failed", e)
                return false
            }
        },
        fetchLocalSongs,
        deleteSong,
        updateSongInList,
        sortField,
        sortOrder
    }
})
