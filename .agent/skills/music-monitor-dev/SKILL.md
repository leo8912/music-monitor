---
name: music-monitor-dev
description: 音乐监控项目专用开发指南。包含架构模式、UI规范（Spotify暗黑风）及GDStudio接口参考。
trigger: 触发词: [音乐监控开发, 架构规范, 前端规范, GDStudio接口, API参考]
---

# 音乐监控开发指南 (Music Monitor Development Guide)

此技能是开发、重构和维护 Music Monitor 项目的权威指南。

## 1. 项目架构 (Project Architecture)

本项目遵循严格的 **Service-Repository** 模式，关注点分离清晰。

### 分层结构
1.  **routers/ (`app/routers/`)**:
    *   **职责**: 处理 HTTP 请求/响应，输入验证 (Pydantic)，调用 Services。
    *   **限制**: 禁止直接访问数据库。禁止包含复杂业务逻辑。
2.  **services/ (`app/services/`)**:
    *   **职责**: 实现业务逻辑，编排对 Repositories 和外部音乐提供者 (Music Providers) 的调用。
    *   **限制**: 禁止直接编写 SQL 查询 (必须通过 Repositories)。
3.  **repositories/ (`app/repositories/`)**:
    *   **职责**: 封装所有数据库交互 (CRUD)。
    *   **限制**: 禁止包含业务逻辑。仅返回 ORM 模型。
4.  **music_providers/ (`app/services/music_providers/`)**:
    *   **职责**: 对接外部 API (QQ音乐, 网易云)。
    *   **模式**: 所有提供者必须继承 `MusicProvider` 基类。

### 核心规则
*   **依赖注入**: 使用 FastAPI 的 `Depends` 注入 Service 和 Repository。
*   **异步优先**: 所有 I/O 密集型操作 (DB, 网络) 必须是 `async` 的。
*   **会话管理**: 数据库 Session 在 Router 层通过依赖注入管理，并向下传递给 Service/Repository。

## 2. 前端 UI 规范 (Frontend UI Standards)

前端 (Vue 3 + NaiveUI) 必须严格遵循 **"类 Spotify" 暗黑模式** 美学。

### 核心设计指南
*   **主题**: 仅暗黑模式 (Dark Mode Only)。
*   **配色**:
    *   **背景**: `#121212` (基础底色), `#181818` (卡片/表面), `#282828` (悬停/抬起)。
    *   **主色调**: `#1DB954` (Spotify 绿) - 用于主要操作、播放按钮、激活状态。
    *   **文字**: `#FFFFFF` (主要), `#B3B3B3` (次要/元数据)。
*   **视觉计算**:
    *   **圆角 (Border Radius)**: 大圆角设计。按钮: `500px` (胶囊形)。卡片: `8px`。
    *   **交互**: 必须有悬停 (Hover) 效果 (如背景变亮或显示隐藏的播放按钮)。
*   **NaiveUI 覆盖**:
    *   确保所有 NaiveUI 组件 (模态框, 卡片, 输入框) 样式匹配自定义暗黑主题，必要时覆盖默认灰色。

### 组件结构
*   **原子设计**: 使用小型、可复用的组件 (如 `SongCard`, `StatusBadge`)。
*   **API**: 所有 API 调用必须封装在 `web/src/api/` 中。

## 3. 工作流指南 (Workflow Guidelines)

### 添加新的音乐源 (Music Provider)
1.  创建 `app/services/music_providers/new_provider.py`。
2.  继承 `MusicProvider` 类。
3.  实现 `search_song`, `get_song_urls` 等方法。
4.  在 `MusicProviderFactory` (或 Aggregator) 中注册。

### 修改歌曲元数据逻辑
*   **位置**: `app/services/scraper.py` (或相关 Service)。
*   **流程**:
    1.  抓取 (Fetching): 使用 `Aggregator` 搜索。
    2.  下载 (Downloading): 使用 `requests` 或 `aiohttp`。
    3.  标签写入 (Tagging): 使用 `mutagen` 处理 ID3/FLAC 标签 (确保严格类型赋值)。
    4.  持久化 (Persisting): 通过 `SongRepository` 更新 `Song` 模型。

## 4. 提交前检查清单 (Pre-Commit Checklist)

在标记任务完成前，请检查：
1.  **Linting**: 代码整洁，遵循 Python 标准 (PEP 8)。
2.  **类型安全**: 无明显的类型错误 (特别是在 `mutagen` 标签赋值处)。
3.  **UI 验证**:
    *   看起来像 Spotify 吗？
    *   过渡动画是否流畅？
    *   响应式布局是否正常？
4.  **测试**: 运行 `测试/后端/` 下的相关测试脚本。

## 5. 常用命令 (Common Commands)

*   **启动本地开发**: `python main.py` (后端) + `npm run dev` (前端)。
*   **运行测试**: `pytest` 或 `python 测试/后端/xxx.py`。
*   **同步 API 技能**: `python tests/sync_gdstudio_skill.py`.

## 6. 版本控制工作流 (Versioning Workflow)
 
项目使用 `version.py` 作为全栈版本号的唯一真理源 (SSOT)。
 
### 版本升级步骤
1.  修改 `version.py` 中的 `__backend_version__` 和 `__frontend_version__`。
2.  运行 `python scripts/sync_version.py` 同步到 `web/package.json`。
3.  更新 `__build_date__` (或由 CI 自动更新)。
4.  提交信息格式: `chore: bump version to x.y.z`。
5.  推送标签: `git tag vx.y.z && git push origin vx.y.z` (CI 会校验 Tag 与代码版本是否一致)。
 
### 7. CI/CD 与发版 (Deployment)
- **Workflow**: `.github/workflows/docker-publish.yml`
- **策略**: 
    - `main` 分支对应 `latest` 镜像。
    - `v*.*.*` Tag 对应版本镜像。
- **环境一致性**: 
    - Dockerfile 结构需与本地清理后的目录结构保持一致 (`/app` 为根)。
    - DB 迁移必须在容器启动脚本 `entrypoint.sh` 中自动执行。

## 7. GDStudio API 参考 (GDStudio API Reference)

官方实例: `https://music-api.gdstudio.xyz/api.php`

### 稳定源 (Updated 2026-02-05)
*   **推荐**: `netease` (网易云)
*   **推荐**: `joox`
*   **推荐**: `kuwo` (酷我)
*   **问题源**: `tencent` (QQ音乐), `tidal`, `spotify`, `ytmusic`, `qobuz`, `deezer`, `migu`, `kugou`, `ximalaya`, `apple` (当前可能返回 400 或空数据)。
