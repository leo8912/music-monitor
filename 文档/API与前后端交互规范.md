# API 与前后端交互规范

> **版本**: 1.0.0（基于重构前接口）
> **API 基础路径**: `/api`
> **状态**: ⚠️ 已过时，以 OpenAPI (`/docs`) 为准
>
> [!WARNING]
> 本文档编写于重构前。2026-08 重构后接口已按 `app/api/v1/` 重排（拆分 system.py / media.py，
> 新增 response_model 与统一分页），路径与返回结构均有变化。本文档仅作历史参考，
> **实际接口以 FastAPI 自动生成的 `/docs` (OpenAPI) 为准**。

本规范旨在整合前后端数据交换格式，明确各实体的核心字段，以及定义具体的 API 接口交付标准，以减少沟通成本。

## 1. 核心模型数据结构 (Core Schemas)

### 1.1 歌曲对象 (Song)
前端在播放器、列表、历史记录中通用的模型。
- **id**: `int` (数据库唯一 ID)
- **unique_key**: `string` (格式：`provider_mediaid`, 例如 `qqmusic_12345`)
- **title**: `string` (歌名)
- **artist**: `string` (歌手名，多位歌手以 `/` 分格)
- **album**: `string` (专辑名)
- **cover_url**: `string` (图片完整 URL)
- **status**: `enum` (`PENDING` | `DOWNLOADED` | `FAILED` | `PENDING_METADATA`)
- **is_favorite**: `boolean` (收藏状态)
- **local_audio_path**: `string` (后端相对路径，用于文件查找)

---

## 2. API 接口交付文档

### 2.1 资料库管理 (Library)
**获取歌曲列表** 
`GET /api/library/songs`
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

### 2.2 媒体操作 (Media)
**触发下载**
`POST /api/download_audio`
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

**移动端元数据 (带签名验证)**
`GET /api/mobile/metadata`
- **参数**: `id`, `sign`, `expires` (由后端签名生成)
- **说明**: 微信推送专用接口，返回该唯一标识符对应的歌曲完整详情。

### 2.3 搜索与发现 (Discovery)
**搜索歌手**
`GET /api/discovery/search` (由聚合器分发)
- **参数**: `keyword`, `limit`
- **说明**: 并发调用网易云与 QQ 音乐，已包含打分去重逻辑。

---

## 3. 跨层交互规范 (Cross-layer Interaction)

### 3.1 路径管理 (Path Mapping)
- **前端需知**: 不要直接通过数据库存储的 `local_path` 拼接 URL。
- **后端保证**: 通过 `/api/audio/{filename}` 接口映射。物理位置迁移（Cache 变Favorite）对前端需是透明的，仅需更新 `unique_key` 对应的对象属性。

### 3.2 搜索打分与展示
- **去重逻辑**: 后端负责根据 `title` + `artist` 的小写归一化进行聚合。
- **展示顺序**: 优先推荐 `source: "qqmusic"` 且包含封面图片的条目。

### 3.3 全局错误码 (Error Handling)
| HTTP 状态码 | 说明 | 处理方式 |
| :--- | :--- | :--- |
| `200` | 成功 | 解析业务数据 |
| `400` | 参数错误 | 检查请求负载 |
| `403` | 权限不足/签名失效 | 重新发起授权或检查链接有效性 |
| `404` | 资源不存在 | 提示用户资源已下架或路径错误 |
| `500` | 服务器内部错误 | 通常伴随详细消息 (如：下载失败、API 达到频率限制) |

---

## 4. 后端待优化/待支持项 (Backlog for BE)
1. **分词搜索支持**: 目前仅支持精准匹配及简单包含，建议引入模糊搜索。
2. **播放进度同步**: 目前播放器进度完全在前端内存中，建议新增 `PATCH /api/player/progress` 同步接口。
3. **歌词解析**: 建议后端统一将歌词转为 `.lrc` 标准格式返回，而非原始字符串。

> [!TIP]
> **开发环境播放**: 
> 对于本地文件，可以直接访问 `/api/audio/{filename:path}` 进行流式播放。后端支持 Range 请求。

> [!NOTE]
> **实时性说明**: 
> 下载任务的状态变更（PENDING -> DOWNLOADED）建议通过 `/api/download/status/{task_id}` 进行短轮询获取，当前暂未部署 WebSocket。
