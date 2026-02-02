<script setup lang="ts">
/**
 * 登录页面 - Spotify 风格沉浸版
 */

import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore, useLibraryStore } from '@/stores'
import { NIcon, NSpin, useMessage } from 'naive-ui'
import { MusicalNotes, LogoGithub, PersonOutline, LockClosedOutline } from '@vicons/ionicons5'

const router = useRouter()
const userStore = useUserStore()
const libraryStore = useLibraryStore()
const message = useMessage()

const username = ref('')
const password = ref('')
const errorMsg = ref('')

onMounted(async () => {
  // 检查是否已经登录，如果已登录且处于登录页，则尝试跳转
  // router/index.ts 守卫也会处理，但此处作为双重保险
})

const handleLogin = async () => {
    if (!username.value || !password.value) {
        message.warning('请输入用户名和密码')
        return
    }
    
    errorMsg.value = ''
    
    try {
        const result = await userStore.login(username.value, password.value)
        // 增强版判断：只要 result.success 为真，或者消息包含“成功”
        if (result.success || (result.message && result.message.includes('成功'))) {
            // 登录成功时，彻底清除错误状态
            errorMsg.value = ''
            message.success('登录成功')
            
            // 给浏览器一点点时间处理 Cookie 写入（某些环境下即时跳转会导致 guard 读不到新 Cookie）
            setTimeout(async () => {
                // 跳转首页
                await router.push('/')
                // 后台预加载数据
                libraryStore.fetchArtists()
                libraryStore.fetchSongs()
            }, 300)
        } else {
            errorMsg.value = result.message || '登录失败'
            message.error(errorMsg.value)
        }
    } catch (e: any) {
        errorMsg.value = '连接服务器失败: ' + (e.message || 'Unknown')
        message.error(errorMsg.value)
    }
}
</script>

<template>
  <div class="sp-login-view">
    <!-- 动态流动背景 -->
    <div class="animated-bg">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
    </div>

    <div class="login-box-container">
      <div class="glass-card">
        <header class="card-header">
           <div class="brand">
             <div class="logo-circle">
                <n-icon size="40" :component="MusicalNotes" />
             </div>
             <h1>Music Monitor</h1>
           </div>
        </header>

        <div class="card-body">
          <h2 class="welcome-text">欢迎回来</h2>
          <p class="subtitle">登录您的账号以开始监控音乐动态</p>

          <div class="form-group">
            <div class="input-wrapper">
              <n-icon :component="PersonOutline" class="input-icon" />
              <input 
                v-model="username" 
                type="text" 
                placeholder="用户名" 
                @keyup.enter="handleLogin"
                autocomplete="username"
              />
            </div>
          </div>

          <div class="form-group">
            <div class="input-wrapper">
              <n-icon :component="LockClosedOutline" class="input-icon" />
              <input 
                v-model="password" 
                type="password" 
                placeholder="密码" 
                @keyup.enter="handleLogin"
                autocomplete="current-password"
              />
            </div>
          </div>

          <button 
            class="login-btn" 
            @click="handleLogin" 
            :disabled="userStore.isLoading"
          >
            <span v-if="!userStore.isLoading">立即登录</span>
            <n-spin v-else size="small" stroke="#000" />
          </button>

          <div class="error-msg-area" v-if="errorMsg">
             {{ errorMsg }}
          </div>
        </div>

        <footer class="card-footer">
          <div class="divider"></div>
          <p class="signup-text">目前仅支持管理员后台添加账号</p>
          <div class="footer-links">
             <a href="https://github.com" target="_blank">
               <n-icon :component="LogoGithub" />
               GitHub Project
             </a>
          </div>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sp-login-view {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  background: #090909;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 动态背景 blobs */
.animated-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 0;
}

.blob {
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(29, 185, 84, 0.15) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(80px);
  animation: move 20s infinite alternate;
}

.blob-1 { top: -10%; left: -10%; background: radial-gradient(circle, rgba(29, 185, 84, 0.1) 0%, transparent 70%); }
.blob-2 { bottom: -10%; right: -10%; background: radial-gradient(circle, rgba(147, 51, 234, 0.1) 0%, transparent 70%); animation-delay: -5s; }
.blob-3 { top: 40%; left: 30%; width: 400px; height: 400px; background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%); animation-delay: -10s; }

@keyframes move {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(100px, 100px) scale(1.1); }
}

.login-box-container {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 440px;
  padding: 20px;
}

.glass-card {
  background: rgba(24, 24, 24, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  padding: 48px 40px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

.card-header {
  margin-bottom: 40px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo-circle {
  width: 50px;
  height: 50px;
  background: var(--sp-green);
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #000;
  box-shadow: 0 0 20px rgba(29, 185, 84, 0.4);
}

.brand h1 {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.5px;
  margin: 0;
}

.welcome-text {
  font-size: 28px;
  font-weight: 800;
  margin: 0 0 8px 0;
  color: #fff;
}

.subtitle {
  font-size: 14px;
  color: #b3b3b3;
  margin-bottom: 32px;
}

.form-group {
  margin-bottom: 16px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 16px;
  font-size: 18px;
  color: #727272;
}

.input-wrapper input {
  width: 100%;
  height: 54px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: #fff;
  padding: 0 16px 0 48px;
  font-size: 15px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.input-wrapper input:focus {
  outline: none;
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--sp-green);
  box-shadow: 0 0 0 4px rgba(29, 185, 84, 0.1);
}

.login-btn {
  width: 100%;
  height: 54px;
  background: var(--sp-green);
  border: none;
  border-radius: 12px;
  color: #000;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  margin-top: 12px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-btn:hover {
  background: #1ed760;
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(29, 185, 84, 0.3);
}

.login-btn:active {
  transform: translateY(0);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.error-msg-area {
  margin-top: 20px;
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.05); /* 降低背景浓度，不像按钮 */
  padding: 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 77, 79, 0.2);
  font-size: 13px;
  text-align: center;
}

.divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
  margin: 32px 0 24px 0;
}

.signup-text {
  font-size: 13px;
  color: #727272;
  text-align: center;
  margin-bottom: 16px;
}

.footer-links {
  display: flex;
  justify-content: center;
}

.footer-links a {
  color: #b3b3b3;
  text-decoration: none;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: color 0.2s;
}

.footer-links a:hover {
  color: #fff;
}
</style>
