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
    const globalTasks = ref<Record<string, Task>>({})

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

    const updateGlobalTask = (payload: Task) => {
        if (!payload.taskId) return

        globalTasks.value[payload.taskId] = payload

        // Auto-remove completed tasks after a longer delay (e.g. 10s) 
        // or keep them until user dismisses? 
        // Plan said "TaskCenter support manual clear", so keep them.
        // But maybe move to "closed" list? 
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

export interface Task {
    taskId: string
    taskType: string
    state: 'pending' | 'running' | 'paused' | 'cancelling' | 'cancelled' | 'completed' | 'error'
    progress: number
    message: string
    details?: any
    timestamp: number
}
