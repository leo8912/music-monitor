<template>
  <div class="pending-view">
    <header class="view-header">
      <div class="header-main">
        <h1 class="text-huge">待定</h1>
        <div class="header-actions">
          <div class="search-box">
            <n-input
              v-model:value="searchQuery"
              placeholder="搜索歌名 / 歌手 / 专辑..."
              clearable
              round
              size="small"
            >
              <template #prefix>
                <n-icon :component="SearchOutline" />
              </template>
            </n-input>
          </div>
          <n-button quaternary circle @click="handleRefresh" title="刷新列表">
            <template #icon><n-icon :component="RefreshOutline" /></template>
          </n-button>
        </div>
      </div>
      <div class="header-sub">
        <span>关注歌手的新歌会自动下载到这里，试听喜欢后可手动入库，不喜欢的可直接忽略。</span>
      </div>
    </header>

    <div class="view-content">
      <div class="list-wrapper" v-if="pendingSongs.length > 0">
        <SongList
          :history="pagedSongs"
          :loading="loading"
          mode="pending"
          @play="handlePlay"
          @toggleFavorite="handleImport"
          @delete="handleIgnore"
        />
      </div>

      <div
        class="pagination-wrapper footer-pagination"
        v-if="!loading && pendingSongs.length > pageSize"
      >
        <n-pagination
          v-model:page="currentPage"
          :page-count="Math.ceil(pendingSongs.length / pageSize)"
          simple
        />
      </div>

      <div v-if="!loading && pendingSongs.length === 0" class="empty-state">
        <n-empty
          :description="searchQuery.trim() ? '没有找到匹配的待定歌曲' : '暂无待定歌曲，新歌自动下载后会出现在这里'"
        >
          <template #icon>
            <n-icon size="48" :component="CloudDownloadOutline" color="var(--text-tertiary)" />
          </template>
        </n-empty>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 待定视图 - 已下载未入库的歌曲
 *
 * 数据源: 后端 local-songs (本地文件歌曲) 全量拉取后前端过滤:
 *   local_path 位于 cache_dir 内 && 未收藏 (is_favorite=false)。
 *
 * 交互:
 *   - 入库: 收藏 (文件移入 favorites, 记为已入库)
 *   - 忽略: 删除文件 + 删除记录 + 写忽略墓碑 (防监控重新发现)
 */
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NIcon, NEmpty, NInput, NPagination, useMessage, useDialog } from 'naive-ui'
import { RefreshOutline, SearchOutline, CloudDownloadOutline } from '@vicons/ionicons5'
import { useLibraryStore } from '@/stores/library'
import { usePlayerStore } from '@/stores/player'
import { useSettingsStore } from '@/stores/settings'
import * as libraryApi from '@/api/library'
import SongList from '@/components/SongList.vue'
import type { Song } from '@/types'

const message = useMessage()
const dialog = useDialog()
const libraryStore = useLibraryStore()
const playerStore = usePlayerStore()
const settingsStore = useSettingsStore()

const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const allSongs = ref<Song[]>([])

/** 判断 local_path 是否位于缓存目录 (cache_dir) 内 */
const pathInCache = (path: string | undefined, cacheDir: string): boolean => {
    if (!path || !cacheDir) return false
    const normalize = (p: string) => p.replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase()
    const p = normalize(path)
    const c = normalize(cacheDir)
    return p === c || p.startsWith(c + '/')
}

const cacheDir = computed(() => settingsStore.settings?.storage?.cache_dir || '')

/** 过滤: 缓存目录内 + 未收藏 */
const pendingSongs = computed(() => {
    const q = searchQuery.value.trim().toLowerCase()
    return allSongs.value.filter(s => {
        if (s.is_favorite) return false
        if (!pathInCache(s.local_path, cacheDir.value)) return false
        if (!q) return true
        return (
            (s.title || '').toLowerCase().includes(q) ||
            String(s.artist || '').toLowerCase().includes(q) ||
            (s.album || '').toLowerCase().includes(q)
        )
    })
})

const pagedSongs = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    return pendingSongs.value.slice(start, start + pageSize.value)
})

const fetchPending = async () => {
    loading.value = true
    try {
        // 全量拉取本地歌曲 (前端过滤缓存目录与收藏状态)
        const result = await libraryApi.getLocalSongs({
            page: 1,
            page_size: 500,
            sortBy: 'created_at',
            order: 'desc'
        })
        // @ts-ignore 后端 SongPayload 字段
        allSongs.value = (result.items || []).map((s: any) => ({
            id: s.id,
            title: s.title,
            artist: s.artist,
            album: s.album || '',
            source: (s.source || 'local') as any,
            source_id: s.source_id || '',
            cover: s.cover || s.pic_url,
            local_path: s.local_path,
            is_favorite: s.is_favorite || false,
            status: (s.status || 'DOWNLOADED') as any,
            publish_time: s.publish_time,
            created_at: s.created_at,
            available_sources: s.available_sources || [],
            quality: s.quality,
            local_files: s.local_files || []
        }))
    } catch (error) {
        console.error('获取待定歌曲失败:', error)
        message.error('获取待定歌曲失败')
    } finally {
        loading.value = false
    }
}

const handleRefresh = async () => {
    await fetchPending()
    message.success('列表已刷新')
}

const handlePlay = (song: Song) => {
    playerStore.setPlaylist(pendingSongs.value)
    playerStore.playSong(song)
}

/** 入库: 收藏歌曲 */
const handleImport = async (song: Song) => {
    const success = await libraryStore.toggleFavorite(song)
    if (success) {
        message.success(`已将「${song.title}」入库收藏`)
        allSongs.value = allSongs.value.filter(s => s.id !== song.id)
    } else {
        message.error('入库失败')
    }
}

/** 忽略: 删除文件 + 删除记录 + 写墓碑 */
const handleIgnore = (song: Song) => {
    dialog.warning({
        title: '确认忽略',
        content: `确认忽略「${song.title}」吗？将删除文件与记录，此后不再监控推送此歌曲。`,
        positiveText: '确认忽略',
        negativeText: '取消',
        onPositiveClick: async () => {
            const success = await libraryStore.deleteSong(song)
            if (success) {
                message.success(`已忽略「${song.title}」，不再监控推送`)
                allSongs.value = allSongs.value.filter(s => s.id !== song.id)
            } else {
                message.error('忽略失败')
            }
        }
    })
}

watch(searchQuery, () => { currentPage.value = 1 })

onMounted(async () => {
    if (!settingsStore.settings) {
        await settingsStore.fetchSettings()
    }
    await fetchPending()
})
</script>

<style scoped>
.pending-view {
  padding-bottom: 32px;
}

.view-header {
  margin-bottom: 24px;
}

.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-box {
  width: 240px;
}

.header-sub {
  color: var(--text-secondary, #b3b3b3);
  font-size: 13px;
}

.view-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.list-wrapper {
  min-height: 200px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
}

.empty-state {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}
</style>
