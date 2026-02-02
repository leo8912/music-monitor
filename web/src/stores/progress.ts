import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ArtistProgress {
    artistId: number
    artistName: string
    state: 'pending' | 'scanning' | 'matching' | 'rescue' | 'complete' | 'error'
    progress: number
    message: string
    timestamp: number
}

export const useProgressStore = defineStore('progress', () => {
    const tasks = ref<Record<number, ArtistProgress>>({})

    const updateProgress = (payload: any) => {
        const { artistId, state } = payload

        tasks.value[artistId] = {
            ...payload,
            timestamp: Date.now()
        }

        if (state === 'complete' || state === 'error') {
            setTimeout(() => {
                delete tasks.value[artistId]
            }, 3000)
        }
    }

    const getProgress = (artistId: number) => {
        return tasks.value[artistId]
    }

    return {
        tasks,
        updateProgress,
        getProgress
    }
})
