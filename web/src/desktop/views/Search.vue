<template>
  <div class="search-view">
    <header class="view-header">
      <div class="search-input-container">
        <n-icon size="24" :component="SearchOutline" class="search-icon" />
        <input 
          v-model="keyword" 
          type="text" 
          placeholder="搜索资源并下载..." 
          @keyup.enter="handleSearch"
          class="search-input"
        />
        <button v-if="keyword" class="clear-btn" @click="keyword = ''">
          <n-icon size="20" :component="CloseCircleOutline" />
        </button>
      </div>
    </header>

    <!-- 移除标签切换，仅保留资源模式 -->

    <main class="view-content">
      <!-- 默认状态: 无关键词 -->
      <div v-if="!keyword" class="empty-state">
          <div class="empty-content">
              <h3>资源搜索</h3>
              <p>输入关键词，寻找并下载您喜爱的音乐资源。</p>
          </div>
      </div>

      <!-- 有关键词 -->
      <!-- 仅显示资源结果 -->
      <template v-else>
         <DownloadList
            v-if="results.length > 0 || isLoading"
            :items="results"
            :loading="isLoading"
            @download="handleDirectDownload"
         />
         <div v-else class="empty-state">
             <div class="empty-content">
                 <h3>无资源</h3>
                 <p>未找到可下载的资源，或者服务暂不可用。</p>
             </div>
         </div>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
/**
 * 桌面端搜索视图 - Spotify 风格
 */
import { ref } from 'vue'
import { NIcon, NSpin, useMessage } from 'naive-ui'
import { SearchOutline, CloseCircleOutline } from '@vicons/ionicons5'
import { searchDownload } from '@/api/discovery'
import { usePlayerStore, useLibraryStore } from '@/stores'
import DownloadList from '@/components/DownloadList.vue'

const keyword = ref('')
const activeType = ref('resource') // 默认为资源模式
const isLoading = ref(false)
const results = ref<any[]>([])

const playerStore = usePlayerStore()
const libraryStore = useLibraryStore()
const message = useMessage()

const handleSearch = async () => {
  if (!keyword.value.trim()) return
  isLoading.value = true
  results.value = [] // clear previous
  try {
    results.value = await searchDownload({ keyword: keyword.value, limit: 30 })
  } catch (e) {
    console.error(e)
    message.error('搜索服务响应异常')
  } finally {
    isLoading.value = false
  }
}

const handleDirectDownload = async (item: any) => {
    // 设置局部 loading 状态
    item._loading = true
    message.loading(`正在开始下载: ${item.title}...`)
    
    try {
        const success = await libraryStore.downloadSong({
            title: item.title,
            artist: item.artist,
            album: item.album,
            source: item.source,
            source_id: item.id,
            quality: item.quality,
            cover_url: item.cover_url
        })
        
        if (success) {
            message.success(`下载成功: ${item.title}`)
        } else {
            message.error(`下载失败: ${item.title}`)
        }
    } catch (e) {
        message.error(`下载异常: ${e}`)
    } finally {
        item._loading = false
    }
}
</script>

<style scoped>
.search-view {
  padding: 24px 32px;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100%;
}

.view-header {
  margin-bottom: 24px;
}

.search-input-container {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 500px;
  background: #fff;
  max-width: 400px;
  height: 48px;
  color: #121212;
}

.search-icon { color: #121212; }

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 16px;
  color: #121212;
  font-weight: 500;
}
.search-input::placeholder { color: #555; }

.clear-btn {
    background: none; border: none; color: #121212; cursor: pointer; display: flex;
}


.empty-state {
  padding: 100px 0;
  display: flex;
  justify-content: center;
  text-align: center;
  color: var(--text-primary);
}

.empty-content h3 { font-size: 24px; margin-bottom: 8px; }
.empty-content p { color: var(--text-secondary); }
</style>
