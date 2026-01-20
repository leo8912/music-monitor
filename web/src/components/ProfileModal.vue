<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'
import { NModal, NIcon, NButton, useMessage, NUpload } from 'naive-ui'
import { CloseOutline, PersonCircleOutline, LogOutOutline, CloudUploadOutline } from '@vicons/ionicons5'

const props = defineProps({
  show: { type: Boolean, default: false }
})

const emit = defineEmits(['update:show', 'profile-updated'])

const message = useMessage()
const showEditProfile = ref(false)
const showPasswordForm = ref(false)
const updatingProfile = ref(false)
const changingPassword = ref(false)
const imageLoadError = ref(false)

const currentUser = ref({ name: 'Administrator', avatar: '', role: '超级管理员' })

// 统计信息
const profileStats = ref({
    artistCount: 0,
    songCount: 0,
    cacheSize: '0 MB'
})

const profileForm = ref({
    username: '',
    avatar: ''
})

const passwordForm = ref({
    old_password: '',
    new_password: '',
    confirm_password: ''
})

watch(() => props.show, async (val) => {
    if (val) {
        imageLoadError.value = false
        try {
            const res = await axios.get('/api/check_auth')
            if (res.data.authenticated) {
                currentUser.value.name = res.data.user
                currentUser.value.avatar = res.data.avatar || ''
                // Init form
                profileForm.value.username = res.data.user
                profileForm.value.avatar = res.data.avatar || ''
            }
        } catch (e) {
            console.error("Fetch profile failed", e)
        }
        
        // 获取统计信息
        try {
            const statsRes = await axios.get('/api/profile_stats')
            if (statsRes.data) {
                profileStats.value.artistCount = statsRes.data.artist_count || 0
                profileStats.value.songCount = statsRes.data.song_count || 0
                profileStats.value.cacheSize = statsRes.data.cache_size || '0 MB'
            }
        } catch (e) {
            // 轻量失败，用默认值
            console.warn("Fetch stats failed", e)
        }
    }
})

const handleUpdateProfile = async () => {
    if (!profileForm.value.username) {
         message.warning("用户名不能为空")
         return
    }
    
    updatingProfile.value = true
    try {
        await axios.post('/api/update_profile', profileForm.value)
        message.success("个人资料已更新")
        
        // Update local view
        currentUser.value.name = profileForm.value.username
        currentUser.value.avatar = profileForm.value.avatar
        showEditProfile.value = false
        
        emit('profile-updated', { 
            username: profileForm.value.username,
            avatar: profileForm.value.avatar
        })
        
    } catch (e) {
        message.error("更新失败: " + (e.response?.data?.detail || e.message))
    } finally {
        updatingProfile.value = false
    }
}

// 头像上传逻辑
const handleUpload = async ({ file, onFinish, onError }) => {
    const formData = new FormData()
    formData.append('file', file.file)
    
    try {
        const res = await axios.post('/api/upload_avatar', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        
        if (res.data.status === 'success') {
            profileForm.value.avatar = res.data.url
            // Update current user preview immediately
            currentUser.value.avatar = res.data.url
            imageLoadError.value = false
            message.success('头像上传成功')
            // Emit update to parent
            emit('profile-updated', { avatar: res.data.url })
            onFinish()
        } else {
            message.error('上传失败')
            onError()
        }
    } catch (e) {
        message.error('上传出错: ' + (e.response?.data?.detail || e.message))
        onError()
    }
}

const handleChangePassword = async () => {
    if (!passwordForm.value.old_password || !passwordForm.value.new_password) {
        message.warning("请填写完整")
        return
    }
    if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
        message.error("两次新密码输入不一致")
        return
    }
    
    changingPassword.value = true
    try {
        await axios.post('/api/change_password', {
            old_password: passwordForm.value.old_password,
            new_password: passwordForm.value.new_password
        })
        message.success("修改成功，正在通过新密码重新登录...")
        // Wait a bit then redirect
        setTimeout(() => {
            window.location.href = '/login'
        }, 1500)
    } catch (e) {
        message.error("修改失败: " + (e.response?.data?.detail || e.message))
    } finally {
        changingPassword.value = false
    }
}

const handleLogout = async () => {
    try {
        await axios.post('/api/logout')
        message.success("已退出登录")
        setTimeout(() => window.location.href = '/login', 500)
    } catch (e) {
        message.error("退出失败")
    }
}
</script>

<template>
    <n-modal :show="show" @update:show="$emit('update:show', $event)" class="settings-modal-ios profile-modal" :mask-closable="true">
        <div class="ios-settings-container profile-container">
            <!-- Header -->
            <div class="ios-header">
                <div class="ios-title">账户</div>
                <div class="ios-close-btn" @click="$emit('update:show', false)">
                    <n-icon size="22"><CloseOutline /></n-icon>
                </div>
            </div>

            <!-- Content -->
            <div class="ios-content">
                <!-- User Card (Apple Music Style) -->
                <div class="profile-header-card">
                    <div class="profile-avatar-wrapper">
                        <img 
                            v-if="currentUser.avatar && !imageLoadError" 
                            :src="currentUser.avatar.includes('?') ? currentUser.avatar + '&t=' + Date.now() : currentUser.avatar + '?t=' + Date.now()" 
                            class="avatar-img" 
                            @error="imageLoadError = true"
                        />
                        <div v-else class="avatar-placeholder">
                            <n-icon size="48"><PersonCircleOutline /></n-icon>
                        </div>
                        <!-- Edit Overlay -->
                        <div class="edit-overlay" @click="showEditProfile = !showEditProfile">
                            <span>{{ showEditProfile ? '完成' : '编辑' }}</span>
                        </div>
                    </div>
                    
                    <div class="profile-title-block">
                        <div class="profile-name">{{ currentUser.name }}</div>
                        <div class="profile-role">{{ currentUser.role }}</div>
                    </div>
                </div>

                <!-- Stats Row (Redesigned) -->
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-num">{{ profileStats.artistCount }}</div>
                        <div class="stat-text">关注歌手</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">{{ profileStats.songCount }}</div>
                        <div class="stat-text">歌曲记录</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">{{ profileStats.cacheSize }}</div>
                        <div class="stat-text">本地缓存</div>
                    </div>
                </div>

                <!-- Edit Profile Form -->
                <transition name="slide-fade">
                    <div v-if="showEditProfile">
                        <div class="ios-group-title">个人资料</div>
                        <div class="ios-group">
                             <div class="ios-form-stack">
                                <div class="stack-row">
                                    <span class="label">用户名</span>
                                    <input type="text" v-model="profileForm.username" class="ios-text-input" placeholder="请输入用户名" />
                                </div>
                                <div class="stack-row">
                                    <span class="label">头像</span>
                                    <div class="upload-wrapper">
                                        <!-- Hidden Upload -->
                                        <n-upload
                                            action="/api/upload_avatar"
                                            :custom-request="handleUpload"
                                            :show-file-list="false"
                                            accept="image/png,image/jpeg,image/jpg,image/gif"
                                            class="flex-upload"
                                        >
                                            <span class="upload-text-btn">选择照片</span>
                                        </n-upload>
                                    </div>
                                </div>
                             </div>
                        </div>
                        
                        <div style="padding: 0 16px 24px;">
                             <button class="apple-btn-primary" @click="handleUpdateProfile" :disabled="updatingProfile">
                                 {{ updatingProfile ? '保存中...' : '保存资料' }}
                             </button>
                        </div>
                    </div>
                </transition>

                <div class="ios-group-title">设置</div>
                <div class="ios-group">
                    <!-- Change Password -->
                    <div class="ios-item cursor-pointer" @click="showPasswordForm = !showPasswordForm">
                        <div class="ios-row-main">
                            <span class="ios-label">修改密码</span>
                            <div class="ios-arrow" :class="{ rotated: showPasswordForm }">›</div>
                        </div>
                    </div>

                    <!-- Password Form -->
                    <div v-if="showPasswordForm" class="ios-form-stack" style="background: var(--ios-card-bg);">
                        <div class="stack-row">
                            <input type="password" v-model="passwordForm.old_password" class="ios-text-input" placeholder="旧密码" style="text-align: left; margin-left: 0;" />
                        </div>
                        <div class="stack-row">
                            <input type="password" v-model="passwordForm.new_password" class="ios-text-input" placeholder="新密码" style="text-align: left; margin-left: 0;" />
                        </div>
                        <div class="stack-row" style="border-bottom: none;">
                            <input type="password" v-model="passwordForm.confirm_password" class="ios-text-input" placeholder="确认新密码" style="text-align: left; margin-left: 0;" />
                        </div>
                        <div style="padding: 12px 16px;">
                             <button class="apple-btn-secondary" @click="handleChangePassword" :disabled="changingPassword">
                                 确认修改
                             </button>
                        </div>
                    </div>
                </div>

                <div class="ios-group">
                    <div class="ios-item cursor-pointer" @click="handleLogout">
                        <div class="ios-row-main center-content">
                            <span class="ios-label" style="color: #FF3B30;">退出登录</span>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </n-modal>
</template>


<style scoped>
@import '../assets/ios-settings.css';

/* Animations */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

/* Profile Header - Apple Music Style */
.profile-header-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30px 0;
    margin-bottom: 20px;
}

.profile-avatar-wrapper {
    position: relative;
    width: 100px;
    height: 100px;
    margin-bottom: 16px;
    cursor: pointer;
}

.avatar-img {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    object-fit: cover;
    box-shadow: 0 8px 16px rgba(0,0,0,0.1);
}

.avatar-placeholder {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: linear-gradient(135deg, #FF9A9E 0%, #FECFEF 99%, #FECFEF 100%); /* Placeholder Gradient */
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFF;
}

.edit-overlay {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(0,0,0,0.4);
    height: 30px;
    border-bottom-left-radius: 50px; /* Hacky way but works visually for circle bottom */
    border-bottom-right-radius: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 11px;
    font-weight: 600;
    opacity: 0;
    transition: opacity 0.2s;
    overflow: hidden;
    border-radius: 0 0 50px 50px;
    width: 100%;
}

.profile-avatar-wrapper:hover .edit-overlay {
    opacity: 1;
}

.profile-title-block {
    text-align: center;
}

.profile-name {
    font-size: 24px;
    font-weight: 700;
    color: var(--ios-text-color);
    margin-bottom: 4px;
}

.profile-role {
    font-size: 15px;
    color: var(--ios-subtext);
}

/* Stats Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 30px;
}

.stat-box {
    background: var(--ios-item-bg); /* Use item background */
    padding: 16px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    transition: background 0.3s;
}

.stat-num {
    font-size: 20px;
    font-weight: 700;
    color: var(--apple-music-red); /* Accent Color */
}

.stat-text {
    font-size: 12px;
    color: var(--ios-subtext);
    margin-top: 4px;
    font-weight: 500;
    text-transform: uppercase;
}

/* Custom Buttons */
.apple-btn-primary {
    width: 100%;
    padding: 12px;
    border-radius: 12px;
    border: none;
    background: var(--apple-music-red);
    color: white;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.1s;
}

.apple-btn-primary:active {
    transform: scale(0.98);
    opacity: 0.9;
}

.apple-btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.apple-btn-secondary {
    width: 100%;
    padding: 10px;
    border-radius: 10px;
    border: 1px solid var(--apple-music-red);
    background: transparent;
    color: var(--apple-music-red);
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
}

.upload-wrapper {
    flex: 1;
    display: flex;
    justify-content: flex-end;
}

.flex-upload {
    display: inline-block;
}

.upload-text-btn {
    color: var(--apple-music-red);
    font-size: 17px;
    cursor: pointer;
}

.center-content {
    justify-content: center;
}
</style>
