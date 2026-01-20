<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { NModal, NIcon, NSpin, useMessage } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'

const props = defineProps({
  show: { type: Boolean, default: false }
})

const emit = defineEmits(['update:show', 'added'])

const message = useMessage()
const newArtistName = ref('')
const adding = ref(false)

const addArtistSmart = async () => {
    if (!newArtistName.value.trim()) return;
    
    adding.value = true
    try {
        const res = await axios.post('/api/artists', { name: newArtistName.value })
        newArtistName.value = ''
        message.success(res.data.message || "已添加")
        emit('added')
        emit('update:show', false)
    } catch (e) {
        message.error("添加失败: " + (e.response?.data?.detail || e.message))
    } finally {
        adding.value = false
    }
}

const vAutofocus = {
  mounted: (el) => el.focus()
}
</script>

<template>
    <n-modal :show="show" @update:show="$emit('update:show', $event)" class="spotlight-modal" :mask-closable="true">
        <div class="spotlight-content">
            <div class="spotlight-icon">
                <n-icon><SearchOutline /></n-icon>
            </div>
            <input 
                v-model="newArtistName" 
                class="spotlight-input" 
                placeholder="搜索并添加歌手 (如: 陈奕迅)..."  
                @keyup.enter="addArtistSmart"
                v-autofocus
            />
            <div class="spotlight-loader" v-if="adding">
                <n-spin size="small" />
            </div>
        </div>
    </n-modal>
</template>

<style scoped>
/* Spotlight Modal */
:deep(.spotlight-modal) {
    background: transparent;
    box-shadow: none;
}
.spotlight-content {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(20px);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    gap: 16px;
    width: 600px;
    max-width: 90vw;
    border: 1px solid rgba(0,0,0,0.05);
}

.spotlight-icon {
    font-size: 24px;
    color: var(--text-secondary);
}

.spotlight-input {
    flex: 1;
    border: none;
    background: transparent;
    font-size: 22px;
    outline: none;
    color: #333; /* Fallback */
}
.spotlight-input::placeholder {
    color: #999;
}
</style>
