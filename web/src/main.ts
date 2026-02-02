/**
 * 应用入口
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// 样式

import './style.css'

// 创建应用
const app = createApp(App)

// 使用 Pinia
app.use(createPinia())

// 使用路由
app.use(router)

// 挂载
app.mount('#app')
