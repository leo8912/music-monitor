<template>
  <div class="task-center-panel">
    <div class="header">
      <span class="title">任务中心</span>
      <n-button text size="tiny" @click="clearHistory" v-if="hasHistory">
        清除记录
      </n-button>
    </div>

    <!-- Active Tasks -->
    <div class="section-title" v-if="activeTasks.length > 0">进行中</div>
    <n-scrollbar style="max-height: 300px">
      <div v-if="activeTasks.length === 0 && recentTasks.length === 0" class="empty-state">
        暂无活跃任务
      </div>
      
      <div class="task-list">
        <div v-for="task in activeTasks" :key="task.id" class="task-item active">
          <div class="task-icon">
            <n-spin size="small" v-if="task.state === 'running'" />
            <n-icon v-else size="20" :component="TimeOutline" />
          </div>
          <div class="task-content">
             <div class="task-main">
                <span class="task-msg">{{ task.message }}</span>
                <span class="task-pct">{{ task.progress }}%</span>
             </div>
             <n-progress
               type="line"
               :percentage="task.progress"
               :show-indicator="false"
               processing
               class="task-progress"
               size="small"
               :status="taskStatus(task)"
             />
             <div class="task-details" v-if="task.details">
                <span v-if="task.details.healed">已修复: {{ task.details.healed }}</span>
                <span v-if="task.details.new">新增: {{ task.details.new }}</span>
             </div>
          </div>
        </div>

        <!-- Recent/History -->
        <div class="section-title" v-if="recentTasks.length > 0">已完成</div>
        <div v-for="task in recentTasks" :key="task.id" class="task-item history">
          <div class="task-icon">
             <n-icon v-if="task.state === 'completed'" size="20" color="#1DB954" :component="CheckmarkCircleOutline" />
             <n-icon v-else size="20" color="#ff4d4f" :component="AlertCircleOutline" />
          </div>
          <div class="task-content">
             <div class="task-main">
                <span class="task-msg">{{ task.message }}</span>
                <span class="task-time">{{ formatTime(task.timestamp) }}</span>
             </div>
          </div>
        </div>
      </div>
    </n-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useProgressStore, type Task } from '@/stores/progress'
import { CheckmarkCircleOutline, AlertCircleOutline, TimeOutline } from '@vicons/ionicons5'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

const progressStore = useProgressStore()

// Filter active tasks (running/pending) from globalTasks AND tasks (artist)
const activeTasks = computed(() => {
    const globals = Object.values(progressStore.globalTasks).filter(t => 
        t.state === 'running' || t.state === 'pending'
    )
    // Merge artist tasks (convert to generic Task format if needed, but they are different)
    // For MVP, focus on global tasks. Artist tasks are usually short lived.
    return globals.sort((a, b) => b.timestamp - a.timestamp)
})

const recentTasks = computed(() => {
    return Object.values(progressStore.globalTasks).filter(t => 
        t.state === 'completed' || t.state === 'error'
    ).sort((a, b) => b.timestamp - a.timestamp)
})

const hasHistory = computed(() => recentTasks.value.length > 0)

const clearHistory = () => {
    // Need an action in store to clear history
    // For now, manually remove locally (store logic needs update to support clear)
    // Or just filter in computed? But state persists.
    // Let's assume store allows modification or we just hide them.
    for (const t of recentTasks.value) {
        delete progressStore.globalTasks[t.id]
    }
}

const taskStatus = (task: Task) => {
    if (task.state === 'error') return 'error'
    if (task.state === 'completed') return 'success'
    return 'default'
}

const formatTime = (ts: number) => {
    try {
        return formatDistanceToNow(ts, { addSuffix: true, locale: zhCN })
    } catch {
        return ''
    }
}
</script>

<style scoped>
.task-center-panel {
    width: 320px;
    padding: 8px 0;
}
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 16px 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.title {
    font-weight: 600;
    font-size: 14px;
}
.section-title {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
    margin: 12px 16px 4px;
}
.empty-state {
    padding: 24px;
    text-align: center;
    color: rgba(255, 255, 255, 0.3);
    font-size: 13px;
}
.task-item {
    display: flex;
    align-items: flex-start;
    padding: 8px 16px;
    gap: 12px;
}
.task-item:hover {
    background: rgba(255, 255, 255, 0.05);
}
.task-icon {
    padding-top: 2px;
    width: 20px;
}
.task-content {
    flex: 1;
    min-width: 0;
}
.task-main {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
}
.task-msg {
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.task-pct, .task-time {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
    flex-shrink: 0;
    margin-left: 8px;
}
.task-details {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.4);
    margin-top: 4px;
    display: flex;
    gap: 8px;
}
</style>
