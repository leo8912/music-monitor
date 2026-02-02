import { defineStore } from 'pinia'
import { useProgressStore } from './progress'
import { useLibraryStore } from './library'

export const useWebSocketStore = defineStore('websocket', {
    state: () => ({
        socket: null as WebSocket | null,
        isConnected: false,
        reconnectAttempts: 0
    }),
    actions: {
        connect() {
            if (this.socket) return

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const host = window.location.host
            // Ensure /ws/progress is proxied in vite.config.ts if running on dev port
            const url = `${protocol}//${host}/ws/progress`

            this.socket = new WebSocket(url)

            this.socket.onopen = () => {
                this.isConnected = true
                this.reconnectAttempts = 0
                console.log('[WebSocket] Connected')
            }

            this.socket.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data)

                    if (data.type === 'notification') {
                        const level = data.level || 'info'
                        const msg = data.message || ''

                        // @ts-ignore
                        const $message = window.$message
                        if ($message) {
                            if (level === 'success') $message.success(msg, { duration: 3000 })
                            else if (level === 'error') $message.error(msg, { duration: 5000 })
                            else if (level === 'warning') $message.warning(msg, { duration: 4000 })
                            else $message.info(msg, { duration: 3000 })
                        } else {
                            console.log(`[Notification ${level}] ${msg}`)
                        }
                    } else if (data.type === 'artist_progress') {
                        const progressStore = await import('./progress')
                        progressStore.useProgressStore().updateProgress(data)

                        // Sync artist song count immediately when finished
                        if (data.state === 'complete' && data.songCount !== undefined) {
                            const libraryStore = await import('./library')
                            const artist = libraryStore.useLibraryStore().artists.find(a => String(a.id) === String(data.artistId))
                            if (artist) {
                                artist.songCount = data.songCount
                            }
                        }
                    } else if (data.type === 'download_progress') {
                        // Forward to PlayerStore
                        const playerStore = await import('./player')
                        playerStore.usePlayerStore().updateDownloadStatus(data)
                    } else if (data.type === 'refresh_songs' || data.type === 'refresh_list') {
                        // Trigger UI refresh
                        console.log('[WebSocket] Refresh triggered by server')
                        const libraryStore = await import('./library')
                        libraryStore.useLibraryStore().refresh()
                    }
                } catch (e) {
                    // ignore
                    console.error('[WebSocket] Failed to process message:', e)
                }
            }

            this.socket.onclose = () => {
                this.isConnected = false
                this.socket = null

                if (this.reconnectAttempts < 5) {
                    setTimeout(() => {
                        this.reconnectAttempts++
                        this.connect()
                    }, 3000)
                }
            }
        }
    }
})
