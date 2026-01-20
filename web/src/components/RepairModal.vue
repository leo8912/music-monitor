<template>
  <n-modal v-model:show="showModal" preset="card" :title="'修复歌曲: ' + (songInfo?.title || '')" style="width: 600px" transform-origin="center">
    <div class="repair-container">
      <div class="search-box">
        <n-input-group>
          <n-input v-model:value="searchKeyword" placeholder="搜索歌曲、歌手或专辑..." @keypress.enter="handleSearch" />
          <n-button type="primary" @click="handleSearch" :loading="searching">搜索</n-button>
        </n-input-group>
      </div>

      <div class="results-list" v-if="results.length > 0">
        <n-scrollbar style="max-height: 400px">
          <div v-for="item in results" :key="item.source + item.id" class="result-item" @click="confirmRepair(item)">
            <div class="source-icon">
              <img :src="getSourceIcon(item.source)" :title="item.source" />
            </div>
            <div class="song-details">
              <div class="song-title">{{ item.title }}</div>
              <div class="song-meta">{{ formatArtist(item.artist) }} · {{ item.album || '未知专辑' }}</div>
            </div>
            <div class="action-btn">
              <n-button size="small" secondary type="primary">选择</n-button>
            </div>
          </div>
        </n-scrollbar>
      </div>
      
      <n-empty v-else-if="!searching && hasSearched" description="未找到相关歌曲，请尝试更改搜索词" />
      <div v-else-if="searching" class="loading-state">
        <n-spin size="large" />
        <p>正在跨平台搜索...</p>
      </div>
    </div>
  </n-modal>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { NModal, NInput, NInputGroup, NButton, NScrollbar, NEmpty, NSpin, NMessageProvider, NDialogProvider } from 'naive-ui';
import axios from 'axios';

const props = defineProps({
  show: { type: Boolean, default: false },
  songInfo: { type: Object, default: () => ({}) }
});

const emit = defineEmits(['update:show', 'repaired']);

// 使用 computed 来使 showModal 响应式
const showModal = computed({
  get: () => props.show,
  set: (val) => emit('update:show', val)
});

const searchKeyword = ref('');
const searching = ref(false);
const hasSearched = ref(false);
const results = ref([]);

watch(() => props.show, (newVal) => {
  if (newVal && props.songInfo?.title) {
    searchKeyword.value = `${props.songInfo.title} ${props.songInfo.author || props.songInfo.artist || ''}`;
    handleSearch();
  }
});

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) return;
  searching.value = true;
  hasSearched.value = true;
  results.value = [];
  try {
    const res = await axios.get('/api/search_songs', {
      params: { 
        title: props.songInfo?.title || '',
        artist: props.songInfo?.author || props.songInfo?.artist || '',
        album: props.songInfo?.album || ''
      }
    });
    results.value = res.data || [];
  } catch (e) {
    console.error('搜索失败', e);
  } finally {
    searching.value = false;
  }
};

const getSourceIcon = (source) => {
  const icons = {
    netease: 'https://p1.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg',
    qqmusic: 'https://y.gtimg.cn/mediastyle/yqq/img/logo.png',
    kugou: 'https://www.kugou.com/favicon.ico',
    kuwo: 'https://www.kuwo.cn/favicon.ico',
    migu: 'https://www.migu.cn/favicon.ico'
  };
  return icons[source] || '';
};

const formatArtist = (artist) => {
  if (!artist) return '未知歌手';
  if (Array.isArray(artist)) return artist.join(', ');
  return artist;
};

const confirmRepair = async (item) => {
  if (!confirm(`确认要从 ${item.source} 重新下载《${item.title}》吗？这将覆盖现有本地文件。`)) {
    return;
  }
  
  try {
    const res = await axios.post('/api/repair_audio', {
      source: item.source,
      song_id: item.id,
      title: props.songInfo?.title || '',
      artist: props.songInfo?.author || props.songInfo?.artist || '',
      album: item.album || '',
      pic_url: ''
    });
    
    if (res.data.local_path) {
      alert('修复成功，即将重新播放');
      emit('repaired', res.data);
      emit('update:show', false);
    }
  } catch (e) {
    alert('修复失败: ' + (e.response?.data?.detail || e.message));
  }
};
</script>

<style scoped>
.repair-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.result-item:hover {
  background: rgba(0, 122, 255, 0.05);
}
.source-icon img {
  width: 24px;
  height: 24px;
  border-radius: 4px;
}
.song-details {
  flex: 1;
  min-width: 0;
}
.song-title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.song-meta {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  gap: 12px;
  color: #666;
}
</style>
