<template>
  <div v-if="activeTask" class="task-indicator">
      <n-popover trigger="click" placement="bottom-end" style="padding: 0; min-width: 280px;">
          <template #trigger>
              <div class="indicator-trigger">
                  <n-progress
                    type="circle"
                    :percentage="activeTask.progress"
                    :status="progressStatus"
                    :stroke-width="6"
                    style="width: 32px; height: 32px;"
                  >
                   <template #default>
                       <n-icon v-if="isPaused" :component="Pause" size="14" />
                       <span v-else class="progress-text">{{ activeTask.progress }}</span>
                   </template>
                  </n-progress>
              </div>
          </template>
          
          <!-- Popover Content -->
          <div class="task-popover-content">
              <div class="task-header">
                  <span class="task-title">{{ taskTitle }}</span>
                  <n-tag :type="statusType" size="small" round :bordered="false">
                      {{ statusText }}
                  </n-tag>
              </div>
              
              <div class="task-body">
                  <p class="task-message">{{ activeTask.message }}</p>
                  <n-progress 
                    type="line" 
                    :percentage="activeTask.progress" 
                    :status="progressStatus"
                    processing
                    class="task-progress-line"
                  />
                  <div class="task-details" v-if="activeTask.details">
                      <div v-if="activeTask.details.new !== undefined">
                          新增: {{ activeTask.details.new }}
                      </div>
                      <div v-if="activeTask.details.healed !== undefined">
                          已修复: {{ activeTask.details.healed }} / {{ activeTask.details.total }}
                      </div>
                  </div>
              </div>
              
              <div class="task-footer">
                  <n-button-group size="small">
                      <n-button 
                        secondary 
                        @click="togglePause" 
                        :disabled="isCancelling"
                        :loading="loading"
                      >
                          <template #icon>
                              <n-icon :component="isPaused ? Play : Pause" />
                          </template>
                          {{ isPaused ? '继续' : '暂停' }}
                      </n-button>
                      
                      <n-button 
                        secondary 
                        type="error" 
                        @click="handleCancel"
                        :disabled="isCancelling || isCompleted"
                        :loading="loading"
                      >
                          <template #icon>
                              <n-icon :component="Stop" />
                          </template>
                          取消
                      </n-button>
                  </n-button-group>
              </div>
          </div>
      </n-popover>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NPopover, NProgress, NIcon, NTag, NButtonGroup, NButton, useMessage } from 'naive-ui'
import { Pause, Play, Stop } from '@vicons/ionicons5'
import { useProgressStore } from '@/stores/progress'
import { pauseTask, resumeTask, cancelTask } from '@/api/tasks'

const progressStore = useProgressStore()
const message = useMessage()
const loading = ref(false)

// Determine the most relevant active task (prioritize running over pending, or just take first)
const activeTask = computed(() => {
    const tasks = Object.values(progressStore.globalTasks)
    // Filters out completed ones unless we want to show them briefly?
    // Store logic might remove them. Let's show anything not processed as 'closed'
    // But store logic currently keeps them.
    // Let's pick the one with most recent timestamp that is not completed/error, or if all are done, show nothing?
    // Requirement: "Auto-hide when no tasks".
    
    // Sort by timestamp desc
    const active = tasks
        .filter(t => !['completed', 'error', 'cancelled'].includes(t.state))
        .sort((a, b) => b.timestamp - a.timestamp)[0]
        
    return active
})

const isPaused = computed(() => activeTask.value?.state === 'paused')
const isCancelling = computed(() => activeTask.value?.state === 'cancelling')
const isCompleted = computed(() => ['completed', 'error', 'cancelled'].includes(activeTask.value?.state || ''))

const taskTitle = computed(() => {
    switch (activeTask.value?.taskType) {
        case 'scan': return '音频扫描'
        case 'heal': return '元数据治愈'
        default: return '后台任务'
    }
})

const statusType = computed(() => {
    if (isPaused.value) return 'warning'
    if (isCancelling.value) return 'error'
    return 'success'
})

const statusText = computed(() => {
    if (isPaused.value) return '已暂停'
    if (isCancelling.value) return '正在取消'
    return '进行中'
})

const progressStatus = computed(() => {
    if (isPaused.value) return 'warning'
    if (isCancelling.value) return 'error'
    return 'success'
})

const togglePause = async () => {
    if (!activeTask.value) return
    loading.value = true
    try {
        if (isPaused.value) {
            await resumeTask(activeTask.value.taskId)
            message.success('任务已继续')
        } else {
            await pauseTask(activeTask.value.taskId)
            message.warning('任务已暂停')
        }
    } catch (e) {
        message.error('操作失败')
    } finally {
        loading.value = false
    }
}

const handleCancel = async () => {
    if (!activeTask.value) return
    loading.value = true
    try {
        await cancelTask(activeTask.value.taskId)
        message.info('正在取消任务...')
    } catch (e) {
        message.error('取消失败')
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
.task-indicator {
    display: flex;
    align-items: center;
    cursor: pointer;
    transition: transform 0.2s;
}

.task-indicator:hover {
    transform: scale(1.1);
}

.indicator-trigger {
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 50%;
    padding: 2px;
}

.progress-text {
    font-size: 10px;
    font-weight: bold;
}

.task-popover-content {
    padding: 12px;
    min-width: 250px;
}

.task-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.task-title {
    font-weight: bold;
    font-size: 14px;
}

.task-body {
    margin-bottom: 12px;
}

.task-message {
    font-size: 12px;
    color: var(--n-text-color-3);
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 240px;
}

.task-details {
    margin-top: 4px;
    font-size: 11px;
    color: var(--text-tertiary);
    display: flex;
    gap: 8px;
}

.task-footer {
    display: flex;
    justify-content: flex-end;
}
</style>
