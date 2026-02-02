import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
            '@api': resolve(__dirname, 'src/api'),
            '@stores': resolve(__dirname, 'src/stores'),
            '@types': resolve(__dirname, 'src/types'),
            '@desktop': resolve(__dirname, 'src/desktop'),
            '@mobile': resolve(__dirname, 'src/mobile'),
            '@composables': resolve(__dirname, 'src/composables'),
        }
    },
    server: {
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true
            },
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true
            },
            '/uploads': {
                target: 'http://localhost:8000',
                changeOrigin: true
            }
        }
    },
    build: {
        outDir: 'dist',
        sourcemap: false,
    }
})
