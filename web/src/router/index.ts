/**
 * 路由配置
 * 
 * 仅保留桌面端路由
 */

import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { checkAuth } from '@/api/auth'

const routes: RouteRecordRaw[] = [
    // ========== 桌面端路由 ==========
    {
        path: '/',
        name: 'Home',
        component: () => import('@/desktop/views/Home.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/library',
        name: 'Library',
        component: () => import('@/desktop/views/Library.vue'),
        meta: { requiresAuth: true }
    },

    {
        path: '/settings',
        name: 'Settings',
        component: () => import('@/desktop/views/Settings.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/search',
        name: 'Search',
        component: () => import('@/desktop/views/Search.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/history',
        name: 'History',
        component: () => import('@/desktop/views/History.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/profile',
        name: 'Profile',
        component: () => import('@/desktop/views/Settings.vue'), // 暂时指向设置页
        meta: { requiresAuth: true }
    },
    {
        path: '/artist/:id',
        name: 'ArtistDetail',
        component: () => import('@/desktop/views/ArtistDetail.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/lyrics',
        name: 'Lyrics',
        component: () => import('@/views/LyricsView.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/Login.vue'),
        meta: {}
    },

    // ========== 兼容旧路由 ==========
    {
        path: '/main',
        redirect: '/'
    }
]

const router = createRouter({
    history: createWebHashHistory(),
    routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
    // 登录页特殊处理
    if (to.name === 'Login') {
        try {
            const result = await checkAuth()
            if (result.authenticated) {
                // 已登录，跳转首页
                next({ name: 'Home' })
                return
            }
        } catch { }
        next()
        return
    }

    // 认证检查
    if (to.meta.requiresAuth) {
        try {
            const result = await checkAuth()

            if (result.enabled && !result.authenticated) {
                next({ name: 'Login' })
                return
            }
        } catch (e) {
            console.error('认证检查失败:', e)
            next({ name: 'Login' })
            return
        }
    }

    next()
})

export default router
