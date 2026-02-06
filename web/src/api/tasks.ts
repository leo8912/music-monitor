import { post } from './index'

export interface TaskControlResponse {
    status: string
    task_id: string
}

export function pauseTask(taskId: string) {
    return post<TaskControlResponse>(`/api/tasks/${taskId}/pause`)
}

export function resumeTask(taskId: string) {
    return post<TaskControlResponse>(`/api/tasks/${taskId}/resume`)
}

export function cancelTask(taskId: string) {
    return post<TaskControlResponse>(`/api/tasks/${taskId}/cancel`)
}
