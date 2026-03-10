# Music Monitor 字段命名规范 (Field Naming Convention)

> **此文档是项目字段命名的唯一真理源 (SSOT)**
> 编写代码前必须参考此文档，修改字段名时必须同步更新。

---

## 1. 数据库模型字段 (ORM Models)

### Song (核心歌曲实体)
| 字段名 | 类型 | 说明 | ⚠️ 常见错误 |
|--------|------|------|------------|
| `id` | Integer | 主键 | |
| `unique_key` | String | UUID 去重键 | |
| `artist_id` | Integer | 外键 → Artist.id | |
| `title` | String | 歌曲标题 | |
| `album` | String | 专辑名 | |
| `cover` | String | 封面 URL/路径 | ❌ 不要用 `cover_url` |
| `publish_time` | DateTime | 发布时间 | ❌ 不要用 `datetime.now()` 占位 |
| `created_at` | DateTime | 入库时间 | |
| `is_favorite` | Boolean | 是否收藏 | |
| `status` | String | 状态 (PENDING/DOWNLOADED/ERROR) | |
| `local_path` | String | 本地文件路径 | |
| `last_enrich_at` | DateTime | 上次补全时间 | |

### SongSource (歌曲来源)
| 字段名 | 类型 | 说明 | ⚠️ 常见错误 |
|--------|------|------|------------|
| `source` | String | 平台标识: `qqmusic` / `netease` / `local` | |
| `source_id` | String | 平台歌曲 ID / 文件名 | |
| `cover` | String | 来源封面 | ❌ 不要用 `cover_url` |
| `duration` | Integer | 时长（秒） | |
| `url` | String | 播放链接 | |
| `data_json` | JSON | 扩展数据（见下表） | |

### data_json 内部字段
| 键名 | 类型 | 说明 | ⚠️ 常见错误 |
|------|------|------|------------|
| `quality` | String | 音质标签 (SQ/HQ/PQ) | ❌ 不要用 `quality_info` |
| `format` | String | 文件格式 (FLAC/MP3) | |
| `lyrics` | String | 歌词文本 | |
| `cover` | String | 封面路径 | ❌ 不要用 `cover_url` |
| `bit_rate` | Integer | 比特率 (kbps) | |
| `sample_rate` | Integer | 采样率 (Hz) | |
| `bit_depth` | Integer | 位深度 (bit) | |

### Artist (核心艺术家实体)
| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | Integer | 主键 |
| `name` | String | 歌手名 |
| `avatar` | String | 头像 URL |
| `status` | String | 状态 (active/paused) |
| `last_sync` | DateTime | 上次同步时间 |
| `is_monitored` | Boolean | 是否关注 |

### ArtistSource (艺术家来源)
| 字段名 | 类型 | 说明 |
|--------|------|------|
| `source` | String | 平台标识 |
| `source_id` | String | 平台艺术家 ID |
| `avatar` | String | 来源头像 |
| `url` | String | 来源链接 |
| `raw_data` | JSON | 原始 API 数据 |

---

## 2. API Schema (DTO)

### DownloadRequest
| 字段名 | 类型 | 说明 |
|--------|------|------|
| `source` | str | 平台标识 |
| `song_id` | str | 平台歌曲 ID |
| `title` | str | 歌曲标题 |
| `artist` | str | 歌手名 |
| `album` | str | 专辑名 |
| `pic_url` | str | 封面 URL |

### SongResponse
| 字段名 | 类型 | 说明 | ⚠️ 注意 |
|--------|------|------|---------|
| `cover_url` | str | 封面 URL（API 响应用） | ⚠️ 仅在 **API 响应** 中使用 `cover_url`，模型层用 `cover` |
| `quality` | str | 音质 (SQ/HQ/Hi-Res) | |
| `quality_details` | str | 详细音质 (如 "FLAC \| SQ") | |
| `publish_time` | str | ISO 格式时间字符串 | |

---

## 3. 服务层关键方法签名

### MetadataResult (元数据结果)
| 字段名 | 类型 | 说明 | ⚠️ 常见错误 |
|--------|------|------|------------|
| `lyrics` | str | 歌词 | |
| `cover_data` | bytes | 封面二进制 | |
| `cover_url` | str | 封面 URL | ⚠️ 这里用 `cover_url` 是正确的（尚未持久化） |
| `album` | str | 专辑名 | |
| `publish_time` | str | 发布时间 | |
| `success` | bool | 是否成功 | |
| `source` | str | 数据来源 | |

### DownloadService.download_audio 签名
```python
async def download_audio(
    self,
    title: str,
    artist: str,
    album: str = "",
    quality: int = 999,
    source: str = None,       # 指定源（可选）
    source_id: str = None,    # 指定 ID（可选）
    progress_callback = None
) -> Optional[Dict]
```

### MetadataHealer.heal_song 签名
```python
async def heal_song(
    self,
    song_id: str,
    force: bool = False,
    db = None,                      # 外部会话
    target_source: str = None,      # 指定数据源
    target_song_id: str = None      # 指定歌曲 ID
) -> bool
```

---

## 4. 命名规则总结

### ❌ 禁止的命名
| 错误用法 | 正确用法 | 场景 |
|----------|----------|------|
| `cover_url` | `cover` | ORM 模型和 `data_json` 中 |
| `quality_info` | `quality` | `data_json` 中 |
| `coverUrl` | `cover` | Python 后端 |
| `songCount` | `song_count` | Python 后端（snake_case） |

### ✅ 命名约定
- **Python 后端**: 全部使用 `snake_case`
- **TypeScript 前端**: 使用 `camelCase`
- **API 响应**: 可以有别名映射（如模型 `cover` → 响应 `cover_url`）
- **data_json 键**: 使用 `snake_case`，保持与模型字段一致
- **source 标识**: 固定为 `qqmusic` / `netease` / `local` / `kuwo` / `joox`

### 🔄 模型层 vs API 层 字段对照
| 模型层 (Song) | API 层 (SongResponse) | 说明 |
|---------------|----------------------|------|
| `cover` | `cover_url` | API 层加 `_url` 后缀区分 |
| `local_path` | `local_audio_path` | API 层更具体 |
| `artist.name` | `artist` | API 展平为字符串 |

---

## 5. 单例服务规范

以下服务 **必须使用单例模式**，不可在方法内 `new` 新实例：

| 服务 | 原因 |
|------|------|
| `DownloadService` | 内含 `RateLimiter`，多实例会导致频率限制失效 |
| `MetadataService` | 内含 Provider 缓存 |
| `MusicAggregator` | 内含连接池 |

**正确用法**:
```python
# 全局单例
_download_service = DownloadService()

def get_download_service():
    return _download_service
```
