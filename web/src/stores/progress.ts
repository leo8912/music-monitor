import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Task {
    taskId: string
    taskType: string
    state: 'pending' | 'running' | 'paused' | 'cancelling' | 'cancelled' | 'completed' | 'error'
    progress: number
    message: string
    details?: Record<string, unknown>
    timestamp: number
}

export interface ArtistProgress {
    artistId: number
    artistName: string
    state: 'pending' | 'scanning' | 'matching' | 'rescue' | 'complete' | 'error'
    progress: number
    message: string
    timestamp: number
}

export type ArtistProgressPayload = Partial<Omit<ArtistProgress, 'artistId' | 'timestamp'>> & {
    artistId: number
}

export const useProgressStore = defineStore('progress', () => {
    const tasks = ref<Record<number, ArtistProgress>>({})
    const globalTasks = ref<Record<string, Task>>({})

    const updateProgress = (payload: ArtistProgressPayload) => {
        const { artistId, state } = payload
        tasks.value[artistId] = {
            ...payload,
            artistName: payload.artistName || '',
            state: state || 'pending',
            progress: payload.progress ?? 0,
            message: payload.message || '',
            timestamp: Date.now()
        }
        if (state === 'complete' || state === 'error') {
            setTimeout(() => {
                delete tasks.value[artistId]
            }, 3000)
        }
    }

    const updateGlobalTask = (payload: Task) => {
        if (!payload.taskId) return

        globalTasks.value[payload.taskId] = payload

        // Auto-remove completed tasks after a longer delay (e.g. 10s) 
        // or keep them until user dismisses?
        // TaskCenter 已删除（阶段5.1），任务展示由桌面端任务列表承担。
        // For now, simple reactivity.
        if (payload.state === 'completed' || payload.state === 'error' || payload.state === 'cancelled') {
            // Optional: Auto-dismiss from status bar but keep in history?
            // implemented in UI components
        }
    }

    const getProgress = (artistId: number) => {
        return tasks.value[artistId]
    }

    return {
        tasks,
        globalTasks,
        updateProgress,
        updateGlobalTask,
        getProgress
    }
})
