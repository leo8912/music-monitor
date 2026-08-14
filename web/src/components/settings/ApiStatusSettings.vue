<script setup lang="ts">
/**
 * GDStudio API 接口状态检查 (设置页)
 *
 * 展示网页文档 (music-api.gdstudio.xyz/api.php, 2026-06-26) 列出的
 * 全部音乐源搜索/取链接接口的有效性, 便于监控外部 API 可用状态。
 */
import { onMounted, ref } from 'vue'
import { NSpin, NTag, NButton, NEmpty, NIcon, useMessage } from 'naive-ui'
import { RefreshOutline, PulseOutline, PlayOutline } from '@vicons/ionicons5'
import { getApiHealth, type ApiHealthResult } from '@/api/discovery'

const message = useMessage()
const loading = ref(false)
const testingSource = ref<string | null>(null)
const result = ref<ApiHealthResult | null>(null)

const STABLE_SOURCES = ['netease', 'joox', 'bilibili']
const UNSUPPORTED_SOURCES = ['tencent', 'kuwo', 'tidal', 'qobuz', 'apple', 'ytmusic', 'spotify']

function sourceLabel(source: string): string {
    if (STABLE_SOURCES.includes(source)) return `${source} (稳定)`
    if (UNSUPPORTED_SOURCES.includes(source)) return `${source} (未开放)`
    return source
}

// 状态 → 标签配置
function statusTag(status: string): { type: 'success' | 'warning' | 'error' | 'info' | 'default', text: string } {
    switch (status) {
        case 'ok': return { type: 'success', text: '可用' }
        case 'empty': return { type: 'warning', text: '无结果' }
        case 'unsupported': return { type: 'error', text: '不支持' }
        case 'error': return { type: 'error', text: '异常' }
        case 'skip': return { type: 'default', text: '未测' }
        default: return { type: 'default', text: status }
    }
}

async function load(refresh: boolean = false) {
    if (loading.value) return
    loading.value = true
    try {
        result.value = await getApiHealth(refresh)
        if (refresh && result.value.cached) {
            message.info('检测结果仍为缓存 (180 秒内), 如需立即重测请稍后再试')
        }
    } catch (e) {
        message.error(`接口状态检测失败: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
        loading.value = false
    }
}

// 单源测试: 仅探测指定源并合并进列表
async function testSource(source: string) {
    if (testingSource.value) return
    testingSource.value = source
    try {
        const r = await getApiHealth(true, source)
        const item = r.items[0]
        if (item && result.value) {
            const idx = result.value.items.findIndex(i => i.source === source)
            if (idx >= 0) {
                result.value.items[idx] = item
            } else {
                result.value.items.push(item)
            }
            message.success(`${source}: 测试完成 (${statusTag(item.search_status).text} / ${statusTag(item.url_status).text})`)
        }
    } catch (e) {
        message.error(`${source} 测试失败: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
        testingSource.value = null
    }
}

onMounted(() => load(false))
</script>

<template>
  <div class="api-status-settings">
    <div class="section-header">
      <div class="section-title">
        <span class="title-icon"><n-icon :component="PulseOutline" /></span>
        <span>GDStudio API 接口状态</span>
      </div>
      <div class="section-actions">
        <span v-if="result" class="tested-at">
          检测时间: {{ result.tested_at }}{{ result.cached ? ' (缓存)' : '' }}
        </span>
        <n-button size="small" type="primary" :loading="loading" @click="load(true)">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          全部重新检测
        </n-button>
      </div>
    </div>

    <p class="hint">
      基于网页文档 <code>music-api.gdstudio.xyz/api.php</code> (2026-06-26) 逐源探测
      <code>search</code>(搜索) 与 <code>url</code>(取链接) 接口。每行可单独点击"测试"按钮
      即时重测该源; 全部检测结果缓存 180 秒, 避免触发外部限流 (50次/5分钟)。
    </p>

    <n-spin :show="loading">
      <n-empty v-if="!loading && !result" description="暂无检测结果" style="margin-top: 24px" />
      <table v-else-if="result" class="health-table">
        <thead>
          <tr>
            <th class="col-source">音乐源</th>
            <th class="col-search">搜索接口</th>
            <th class="col-url">取链接接口</th>
            <th class="col-latency">耗时 (搜索/取链)</th>
            <th class="col-msg">说明</th>
            <th class="col-action">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in result.items" :key="item.source">
            <td class="col-source">
              <span class="source-name">{{ sourceLabel(item.source) }}</span>
            </td>
            <td class="col-search">
              <n-tag size="small" :type="statusTag(item.search_status).type" round>
                {{ statusTag(item.search_status).text }}
              </n-tag>
              <span v-if="item.search_count > 0" class="count">×{{ item.search_count }}</span>
            </td>
            <td class="col-url">
              <n-tag size="small" :type="statusTag(item.url_status).type" round>
                {{ statusTag(item.url_status).text }}
              </n-tag>
            </td>
            <td class="col-latency">
              <span v-if="item.search_latency_ms > 0">{{ item.search_latency_ms }}ms</span>
              <span v-if="item.url_latency_ms > 0"> / {{ item.url_latency_ms }}ms</span>
              <span v-else-if="item.search_latency_ms === 0">-</span>
            </td>
            <td class="col-msg">
              <span v-if="item.message" class="msg-text">{{ item.message }}</span>
              <span v-else-if="item.search_status === 'ok' && item.url_status === 'skip'" class="msg-text">搜索可用, 未取链接</span>
              <span v-else class="msg-text">-</span>
            </td>
            <td class="col-action">
              <n-button
                size="tiny"
                type="primary"
                secondary
                :loading="testingSource === item.source"
                :disabled="!!testingSource && testingSource !== item.source"
                @click="testSource(item.source)"
              >
                <template #icon v-if="testingSource !== item.source"><n-icon :component="PlayOutline" /></template>
                测试
              </n-button>
            </td>
          </tr>
        </tbody>
      </table>
    </n-spin>

    <div v-if="result" class="legend">
      <span>图例:</span>
      <n-tag size="small" type="success" round>可用</n-tag>
      <n-tag size="small" type="warning" round>无结果 (200 但空)</n-tag>
      <n-tag size="small" type="error" round>不支持/异常</n-tag>
      <n-tag size="small" type="default" round>未测</n-tag>
    </div>
  </div>
</template>

<style scoped>
.api-status-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}
.title-icon {
  display: inline-flex;
  color: var(--accent-color, #18a058);
}
.section-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tested-at {
  font-size: 12px;
  color: var(--text-color-3, #999);
}
.hint {
  font-size: 12px;
  color: var(--text-color-3, #888);
  margin: 0;
  line-height: 1.6;
}
.hint code {
  background: rgba(127, 127, 127, 0.12);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 11px;
}
.health-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.health-table th,
.health-table td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid rgba(127, 127, 127, 0.15);
}
.health-table th {
  font-weight: 600;
  color: var(--text-color-3, #999);
  font-size: 12px;
}
.health-table tbody tr:hover {
  background: rgba(127, 127, 127, 0.06);
}
.col-source { width: 22%; }
.col-search { width: 14%; }
.col-url { width: 14%; }
.col-latency { width: 18%; }
.col-msg { width: 26%; }
.col-action { width: 10%; text-align: center !important; }
.source-name {
  font-weight: 600;
}
.count {
  margin-left: 6px;
  font-size: 12px;
  color: var(--text-color-3, #999);
}
.msg-text {
  font-size: 12px;
  color: var(--text-color-3, #999);
  word-break: break-all;
}
.legend {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-color-3, #999);
}
</style>
