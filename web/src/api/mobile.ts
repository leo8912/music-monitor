/**
 * 移动端 API（签名链接，无需登录）
 */

import { get } from './index'
import type { MobileMetadata } from '@/types'

// 获取移动端播放元数据
// 注意：拦截器已 unwrap response.data，返回即为元数据对象
export const getMobileMetadata = (params: {
    id: string
    sign: string
    expires: string
}): Promise<MobileMetadata> => {
    return get('/api/mobile/metadata', params)
}