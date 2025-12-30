import { createRouter, createWebHistory } from 'vue-router'
import MainContent from '../MainContent.vue'
import Login from '../Login.vue'
import axios from 'axios'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: MainContent
    },
    {
        path: '/login',
        name: 'Login',
        component: Login
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach(async (to, from, next) => {
    if (to.name === 'Login') {
        // If going to login, check if already auth (optional UX polish)
        try {
            const res = await axios.get('/api/check_auth');
            if (res.data.authenticated) {
                next({ name: 'Home' })
                return
            }
        } catch (e) { }
        next()
        return
    }

    // Protected Routes
    try {
        const res = await axios.get('/api/check_auth')
        if (res.data.enabled && !res.data.authenticated) {
            next({ name: 'Login' })
        } else {
            next()
        }
    } catch (e) {
        // If check fails (network error), maybe let them pass and let API calls fail?
        // Or block. Safety first -> block.
        console.error("Auth check failed", e)
        next({ name: 'Login' })
    }
})

export default router
