/**
 * 路由配置
 * 
 * 支持桌面端和移动端双布局
 */

import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { checkAuth } from '@/api/auth'

// 设备检测
const isMobileDevice = (): boolean => {
    return /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
}

const routes: RouteRecordRaw[] = [
    // ========== 桌面端路由 ==========
    {
        path: '/',
        name: 'Home',
        component: () => import('@/desktop/views/Home.vue'),
        meta: { requiresAuth: true, platform: 'desktop' }
    },
    {
        path: '/library',
        name: 'Library',
        component: () => import('@/desktop/views/Library.vue'),
        meta: { requiresAuth: true, platform: 'desktop' }
    },

    {
        path: '/settings',
        name: 'Settings',
        component: () => import('@/desktop/views/Settings.vue'),
        meta: { requiresAuth: true, platform: 'desktop' }
    },
    {
        path: '/search',
        name: 'Search',
        component: () => import('@/desktop/views/Search.vue'),
        meta: { requiresAuth: true, platform: 'desktop' }
    },
    {
        path: '/history',
        name: 'History',
        component: () => import('@/desktop/views/History.vue'),
        meta: { requiresAuth: true, platform: 'desktop' }
    },
    {
        path: '/profile',
        name: 'Profile',
        component: () => import('@/desktop/views/Settings.vue'), // 暂时指向设置页
        meta: { requiresAuth: true, platform: 'desktop' }
    },
    {
        path: '/artist/:id',
        name: 'ArtistDetail',
        component: () => import('@/desktop/views/ArtistDetail.vue'),
        meta: { requiresAuth: true, platform: 'desktop' }
    },
    {
        path: '/lyrics',
        name: 'Lyrics',
        component: () => import('@/views/LyricsView.vue'),
        meta: { requiresAuth: true, platform: 'desktop' }
    },
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/Login.vue'),
        meta: { platform: 'both' }
    },

    // ========== 移动端路由 ==========
    {
        path: '/mobile',
        name: 'MobileHome',
        component: () => import('@/mobile/views/Home.vue'),
        meta: { requiresAuth: true, platform: 'mobile' }
    },
    {
        path: '/mobile/library',
        name: 'MobileLibrary',
        component: () => import('@/mobile/views/Library.vue'),
        meta: { requiresAuth: true, platform: 'mobile' }
    },
    {
        path: '/mobile/search',
        name: 'MobileSearch',
        component: () => import('@/mobile/views/Search.vue'),
        meta: { requiresAuth: true, platform: 'mobile' }
    },
    {
        path: '/mobile/player',
        name: 'MobilePlayer',
        component: () => import('@/mobile/views/Player.vue'),
        meta: { requiresAuth: true, platform: 'mobile' }
    },
    {
        path: '/mobile/settings',
        name: 'MobileSettings',
        component: () => import('@/mobile/views/Settings.vue'),
        meta: { requiresAuth: true, platform: 'mobile' }
    },
    {
        path: '/mobile/play',
        name: 'MobilePlay',
        // 使用重构后的移动端播放页
        component: () => import('@/mobile/views/Player.vue'),
        meta: { platform: 'mobile' }
    },
    {
        path: '/mobile/artist/:id',
        name: 'MobileArtistDetail',
        component: () => import('@/mobile/views/ArtistDetail.vue'),
        meta: { requiresAuth: true, platform: 'mobile' }
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
    // 微信分享播放页使用签名认证，跳过
    if (to.name === 'MobilePlay') {
        next()
        return
    }

    // 登录页特殊处理
    if (to.name === 'Login') {
        try {
            const result = await checkAuth()
            if (result.authenticated) {
                // 已登录，跳转首页
                next(isMobileDevice() ? { name: 'MobileHome' } : { name: 'Home' })
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

    // 设备自动跳转（可选）
    // if (isMobileDevice() && to.meta.platform === 'desktop') {
    //   next({ path: '/mobile' + to.path })
    //   return
    // }

    next()
})

export default router
