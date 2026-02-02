# Music Monitor 后端 API 参考文档 (Service Layer)

> **创建时间**: 2026-02-02  
> **版本**: v2.1 (Refactored)

本文档详细说明了重构后的服务层（Service Layer）核心 API 及其使用方法。

---

## 1. ArtistRefreshService
负责歌手歌曲列表的抓取、合并与维护。

### `refresh(db, artist_name)`
全量刷新一名歌手的歌曲资料。
- **参数**:
  - `db`: AsyncSession - 数据库会话
  - `artist_name`: str - 歌手名
- **返回**: `int` - 新增歌曲数量
- **描述**: 核心流程包括在线拉取、智能去重、原版查找、孤儿挽救及元数据治愈。

---

## 2. FavoriteService
负责歌曲收藏状态的管理及物理文件移动。

### `toggle(db, song_id)`
切换歌曲收藏状态。
- **参数**:
  - `song_id`: int - 歌曲 ID
- **返回**: `dict` - 包含新状态和文件路径
- **文件逻辑**: 收藏时移动至 `favorites/`，取消收藏时移回 `audio_cache/`。

---

## 3. SongManagementService
负责歌曲和歌手的基础增删改操作。

### `delete_song(db, song_id)`
完全物理删除歌曲。
- **描述**: 同时删除磁盘音频文件和数据库记录。

### `redownload_song(db, song_id, source, source_id, quality=999)`
针对现有歌曲记录发起重新下载。
- **用途**: 用于修复损坏文件或升级音质。

---

## 4. ScanService
本地媒体库自动发现与清理服务。

### `scan_local_files(db, incremental=False)`
扫描本地目录并入库。
- **优化**: V2.1 引入了批量预加载和延迟提交技术，支持数万级文件的快速扫描。

---

## 5. EnrichmentService
元数据智能补全与音质/封面升级。

### `auto_enrich_library(force=False, limit=100)`
自动执行全库标签补全任务。
- **策略**: 优先修复缺失封面和日期的记录。

---

## 技术规范
- **异步支持**: 所有服务方法均为 `async`。
- **错误处理**: 核心方法均受 `@handle_service_errors` 装饰器保护，确保异常时的优雅降级。
- **事务管理**: 外部管理 Session 生命周期，服务方法内部负责具体的 `flush` 和 `commit` 逻辑。
