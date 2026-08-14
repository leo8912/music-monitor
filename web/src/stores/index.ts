/**
 * Stores 统一导出
 *
 * 阶段 5.6: 全部 6 个 store 在此汇总，组件统一从 '@/stores' 导入。
 * 注意：store 之间直接相互 import（如 player→library），不经此 index，
 * 以避免循环依赖。
 */

export { usePlayerStore } from './player'
export { useLibraryStore } from './library'
export { useUserStore } from './user'
export { useSettingsStore } from './settings'
export { useProgressStore } from './progress'
export { useWebSocketStore } from './websocket'
