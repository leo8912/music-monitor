/**
 * Axios 实例配置
 * 
 * 统一的 HTTP 请求封装，包含：
 * - 基础配置
 * - 请求/响应拦截器
 * - 错误处理
 */

import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'

// 创建 axios 实例
const instance: AxiosInstance = axios.create({
    baseURL: '',
    timeout: 30000,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 请求拦截器
instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        // 可以在这里添加 token 等
        return config
    },
    (error: AxiosError) => {
        return Promise.reject(error)
    }
)

// 响应拦截器
instance.interceptors.response.use(
    (response) => {
        return response.data
    },
    (error: AxiosError) => {
        // 统一错误处理
        if (error.response) {
            const status = error.response.status

            if (status === 401) {
                // 未授权，跳转登录
                window.location.hash = '#/login'
            } else if (status === 403) {
                console.error('权限不足')
            } else if (status === 500) {
                console.error('服务器错误')
            }
        }

        return Promise.reject(error)
    }
)

export default instance

// 导出请求方法
export const get = <T>(url: string, params?: object): Promise<T> => {
    return instance.get(url, { params })
}

export const post = <T>(url: string, data?: object): Promise<T> => {
    return instance.post(url, data)
}

export const put = <T>(url: string, data?: object): Promise<T> => {
    return instance.put(url, data)
}

export const del = <T>(url: string): Promise<T> => {
    return instance.delete(url)
}

export const patch = <T>(url: string, data?: object): Promise<T> => {
    return instance.patch(url, data)
}
