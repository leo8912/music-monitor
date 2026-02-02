# API 接口交付文档 (Frontend Delivery)

> **API 基础路径**: `/api`
> **版本**: 1.0.0
> **状态**: 已就绪 (后端 P0 优化已完成)

---

## 1. 资料库管理 (Library)

### 1.1 获取歌曲列表
`GET /library/songs`
- **参数**: 
  - `skip` (int): 分页偏移
  - `limit` (int): 页面大小
  - `artist_name` (optional): 歌手名过滤
  - `is_favorite` (optional): 仅看收藏
- **返回**: 
```json
{
  "items": [
    {
      "id": 1,
      "title": "Song Title",
      "artist": "Artist Name",
      "is_favorite": true,
      "local_path": "audio_cache/xxx.mp3",
      "status": "DOWNLOADED"
    }
  ],
  "total": 100
}
```

---

## 2. 媒体操作 (Media)

### 2.1 触发下载
`POST /download/audio`
- **请求体 (JSON)**:
```json
{
  "source": "qqmusic",
  "song_id": "12345",
  "title": "歌曲名",
  "artist": "歌手名",
  "album": "专辑名"
}
```

### 2.2 移动端元数据 (带签名验证)
`GET /mobile/metadata`
- **参数**: `id`, `sign`, `expires` (由后端签名生成)
- **说明**: 微信推送专用接口，返回该唯一标识符对应的歌曲完整详情。

---

## 3. 搜索与发现 (Discovery)

### 3.1 搜索歌手
`GET /api/search/artist` (由聚合器分发)
- **参数**: `keyword`, `limit`
- **说明**: 并发调用网易云与 QQ 音乐，已包含打分去重逻辑。

---

## 4. 全局错误码 (Error Handling)

| HTTP 状态码 | 说明 | 处理方式 |
| :--- | :--- | :--- |
| `200` | 成功 | 解析业务数据 |
| `400` | 参数错误 | 检查请求负载 |
| `403` | 权限不足/签名失效 | 重新发起授权或检查链接有效性 |
| `404` | 资源不存在 | 提示用户资源已下架或路径错误 |
| `500` | 服务器内部错误 | 通常伴随详细消息 (如：下载失败、API 达到频率限制) |

---

> [!TIP]
> **开发环境播放**: 
> 对于本地文件，可以直接访问 `/api/audio/{filename:path}` 进行流式播放。后端支持 Range 请求。
