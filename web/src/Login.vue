<template>
  <div class="login-container">
    <div class="background-anim"></div>
    
    <div class="login-card">
      <div class="brand">
        <div class="logo-icon">🎵</div>
        <h1>Music Monitor</h1>
      </div>
      
      <div class="input-group">
        <input 
          v-model="username" 
          type="text" 
          placeholder="账号" 
          @keyup.enter="handleLogin"
        />
        <input 
          v-model="password" 
          type="password" 
          placeholder="密码" 
          @keyup.enter="handleLogin"
        />
      </div>

      <button 
        class="login-btn" 
        :class="{ loading: loading }" 
        @click="handleLogin" 
        :disabled="loading"
      >
        <span v-if="!loading">登录系统</span>
        <span v-else class="spinner"></span>
      </button>

      <div class="error-msg" v-if="errorMsg">{{ errorMsg }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

const handleLogin = async () => {
    if (!username.value || !password.value) return
    
    loading.value = true
    errorMsg.value = ''
    
    try {
        await axios.post('/api/login', {
            username: username.value,
            password: password.value
        })
        router.push('/')
    } catch (e) {
        if (e.response && e.response.status === 401) {
            errorMsg.value = '账号或密码错误'
        } else {
            errorMsg.value = '登录失败: ' + (e.message || 'Unknown')
        }
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  position: relative;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
}

.background-anim {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle at 50% 50%, #fa2d48 0%, #4c1d95 30%, #000 70%);
  filter: blur(80px);
  animation: rotate 20s linear infinite;
  opacity: 0.6;
}

@keyframes rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.login-card {
  position: relative;
  width: 320px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(40px) saturate(180%);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}

.brand {
  margin-bottom: 32px;
  text-align: center;
}

.logo-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

h1 {
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.5px;
}

.input-group {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

input {
  width: 100%;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 14px 16px;
  color: white;
  font-size: 16px;
  outline: none;
  transition: all 0.2s;
}

input:focus {
  background: rgba(0, 0, 0, 0.4);
  border-color: rgba(255, 255, 255, 0.3);
}

input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.login-btn {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  background: #fa2d48;
  border: none;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.1s, background 0.2s;
}

.login-btn:active {
  transform: scale(0.98);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.error-msg {
  position: absolute;
  bottom: 12px;
  color: #ff4d4f;
  font-size: 13px;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
