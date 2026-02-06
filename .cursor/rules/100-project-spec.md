# 100-Project Specification & Rules

## 项目介绍
后端项目：集成了 **多平台音乐监控、自动下载** 的全栈解决方案。功能包括自动追踪歌手动态、企业微信推送、网页端播放和收藏。

## 开发规则总览
- **OS**: Windows 系统环境。
- **流程**: 建议 -> 确认 -> 实施。
- **文档**: 计划必须以 md 格式放入文档中，开头备注时间。

## 版本控制 (Versioning)
- **唯一真理 (SSOT)**: `version.py` 是全栈版本号的唯一来源。
- **同步机制**: 
    - 运行 `python scripts/sync_version.py` 自动同步后端版本到 `web/package.json`。
    - 前端必须通过 API (`/api/version`) 动态获取版本号进行展示。
- **发布规范**: 
    - 提交版本更新时，必须同时运行同步脚本。
    - Git Tag (如 `v2.9.5`) 必须与 `version.py` 一致，否则 CI 构建将失败。
- **配置**: `config.example.yaml` 必须随时保持最新。

## 核心业务逻辑
1.  **搜索歌手**:
    - 调用 qqmusic-api、pyncm 搜索列表。
    - 优先从本地数据库获取(如有)。

2.  **添加/刷新**:
    - 获取封面、专辑名、发布日期。
    - 匹配歌手名、歌曲名一致性。
    - 优先本地数据库。

3.  **补全数据**:
    - 补全歌手名、头像、歌词、发布日期。
    - 写入数据库。

4.  **播放逻辑**:
    - **优先本地**: 检查本地媒体库是否有匹配文件 -> 直接播放。
    - **在线下载**: 无匹配 -> 调用 gdstudio 搜索下载无损最高音质。
    - **匹配策略**: 按音乐源顺序搜索，匹配歌手/专辑名一致性并打分，完全一致停止搜索。如果不一致则继续。
    - **翻唱控制**: 确保不下载翻唱歌曲。

5.  **下载限制**:
    - GDStudio API 频率限制: 5分钟 50次。

## API 命名规范 (API Naming Conventions)
- **强制标准**: 所有后端 API 返回的 JSON 字段必须使用 **snake_case** (蛇形命名法)。
- **严禁使用**: 禁止在 API 响应中使用 CamelCase (驼峰命名法) 或 PascalCase。
- **典型纠错**:
    - `availableSources` -> `available_sources` (强制)
    - `publishTime` -> `publish_time` (强制)
    - `localFiles` -> `local_files` (强制)
    - `dataJson` -> `data_json` (强制)
- **前端适配**: 前端通用组件 (如 `SongList.vue`) 必须基于 snake_case 编写。如果对接第三方 API (如网易/QQ) 且字段为驼峰，必须在 Service 层进行转换后再返回给前端。

## 目录结构规范
`app/services/` 需保持解耦。
`music_providers/` 下包含: `base.py`, `netease_provider.py`, `qqmusic_provider.py`, `aggregator.py`.

### 6. 部署与发布 (CI/CD)
- **平台**: GitHub Actions
- **触发机制**:
    - `push to main`: 构建 `latest` 标签镜像。
    - `tag v*.*.*`: 构建对应版本号镜像。
- **构建流程**: Node (Frontend) -> Python (Backend) -> Docker Image。
- **运行时规范**:
    - 容器启动时必须自动运行 `alembic upgrade head`。
    - 必须处理 `PUID`/`PGID` 权限映射。

## 强制技能调用
进行代码修改时，**必须**参考 `music-monitor-dev` (音乐监控开发) 技能：
- 架构决策 -> `1. Project Architecture`
- 前端开发 -> `2. Frontend UI Standards`
- GDStudio -> `6. GDStudio API Reference`
