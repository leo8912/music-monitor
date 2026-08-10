# 音乐监控系统 `music-monitor` 架构审查报告

- **审查对象**：`music-monitor`（后端 FastAPI + SQLAlchemy 2.0/aiosqlite + APScheduler + SQLite；前端 Vue3/Vite）
- **审查人**：高见远（架构师 / software-architect）
- **审查性质**：独立、只读源码审查（未修改任何源码）
- **审查维度**：① 配置管理 ② 分层与模块边界 ③ 数据库层 ④ 安全设计 ⑤ 调度/事件总线/WebSocket ⑥ 可部署性
- **方法**：基于实际源码阅读（`main.py`、`core/*`、`app/routers/*`、`app/services/*`、`app/repositories/*`、`app/models/*`、`alembic/*`、部署文件 `Dockerfile`/`docker-compose.yml`/`requirements.txt`/`.env.example`/`scripts/entrypoint.sh`、`config/config.yaml`），所有结论均标注 `file:line` 依据，无凭空推断。

---

## 0. 架构总览

系统采用经典「路由 → 服务 → 仓储 → 模型」分层，并辅以横切层 `core/`（配置、数据库、调度、安全、事件总线、WebSocket、日志、企业微信）。

```
main.py
  ├─ 中间件: auth_middleware (路径前缀白名单) + SessionMiddleware
  ├─ 路由 routers/
  │    auth / media / system / wechat / version / download_history
  │    metadata / discovery / library / subscription / settings / task_control / websocket
  ├─ 服务 services/
  │    LibraryService(Facade) + ArtistRefresh/Favorite/SongManagement/Scan/MetadataHealer
  │    MediaService / NotificationService / Scheduling / _singletons(Download/Metadata/MusicAggregator)
  ├─ 仓储 repositories/  (base / media_record / song / artist)
  ├─ 模型 models/        (song / artist / base / settings / media_record ...)
  └─ 横切 core/          (config / config_manager / config_migration / database
                          security / scheduler / event_bus / websocket / logger / wechat)
```

**核心矛盾（贯穿全篇）**：系统存在 **两套并行的配置源** —— 遗留的进程内全局字典 `config`（`core/config.py`，直接读写 YAML 文件）与混合配置单例 `ConfigManager`（`core/config_manager.py`，默认值 + YAML 基础设施覆盖 + 数据库业务配置）。二者加载时机、写入方式、数据来源均不一致，是导致配置、安全、模块边界多处缺陷的根因。

---

## 1. 配置管理

### A-01（Critical）— 明文存储密钥与凭据
- **位置**：`config/config.yaml`（已落地明文 `secret_key`、`auth.password`、`notify.wecom.corpsecret/token/encoding_aes_key`）；`core/config_manager.py:77,83`（默认 `secret_key: "CHANGE_ME_IN_ENV_OR_YAML"`、`password: "password"`）；`core/config.py:97`（`ensure_security_config` 以明文返回新密钥）。
- **类别**：安全 / 配置
- **描述**：所有敏感凭据以明文持久化于 YAML 文件（虽被 `.gitignore` 忽略未入库，但宿主机文件即等同于明文泄露）。`secret_key` 用于会话与签名 URL 的 HMAC 计算，`auth.password` 为管理员口令，`corpsecret/token/encoding_aes_key` 为企业微信三方凭证。任何能读取挂载卷的人即可完全接管系统与通知通道。
- **改进建议**：
  1. 敏感字段改用环境变量 / Docker Secret / 独立加密文件（如 `config/secrets.yaml` 600 权限），禁止写入可被日志/API 回显的 `config.yaml`。
  2. 启动时若检测到明文 `secret_key`/`password` 为默认值，**拒绝启动**或强制交互式初始化，而非静默放行。
  3. 引入密钥轮换机制（KMS / 文件权限 600 + 属主 gosu 降权）。

### A-02（High）— 双配置系统数据不一致（源真相分裂）
- **位置**：`core/config.py:17`（`config = {}` 全局字典）vs `core/config_manager.py`（单例）；`app/routers/system.py:170,235`（`config.get('notify')` 读取遗留字典）。
- **类别**：配置 / 一致性
- **描述**：UI 设置页写入数据库 `SystemSettings`（经 ConfigManager），但 `system.py` 的 `/api/test_notify`、`/api/check_notify_status` 仍从遗留全局字典 `config` 读取 `notify`，二者**永不同步**。用户在网页修改通知配置后，测试/连通性检查仍用旧值，产生「改了不生效」的诡异现象。
- **改进建议**：彻底废弃 `core/config.py` 的全局 `config` 字典，所有读取统一走 `get_config_manager().get(...)`；删除 `from core.config import config` 的所有引用（详见 A-11）。

### A-03（High）— 内部可变状态直接对外暴露 / 越权访问私有属性
- **位置**：`app/routers/system.py:67`（`return get_config_manager()._config`）；`app/routers/settings.py:41,145`（同样返回 `._config`）；`app/routers/auth.py:64-66`（`config_manager.data['auth']['username'] = ...`）。
- **类别**：封装 / 安全
- **描述**：
  1. `GET /api/settings` 直接序列化返回整个 `_config` 内部字典，**包含 `secret_key`、`auth.password`、企业微信 `secret` 等明文凭据**（仅 `auth_middleware` 依赖路径白名单拦截，但任何已登录会话均可读取）。
  2. `update_profile` 直接写 `config_manager.data['auth']`——而 `ConfigManager` 并无公开的 `data` 属性（内部为 `_config`），此处依赖私有属性且绕过 `update()`，与内存状态管理脱节。
- **改进建议**：为配置暴露定义只读 Pydantic `Schema`（脱敏 `secret_key`/`password`）；配置写入统一经 `update()` + 持久化方法；禁止路由直接触碰 `_config`/`data`。

### A-04（High）— 失效的 `/api/settings` 写入路径 + 路由重复定义
- **位置**：`app/routers/system.py:69-89`（`@router.post("/api/settings")` 调用 `config_instance.save_config()`）；`core/config_manager.py`（无 `save_config` 方法）；与 `app/routers/settings.py` 同名路由冲突。
- **类别**：正确性 / 模块边界
- **描述**：
  1. `ConfigManager` 仅提供 `get/reload/update`（`config_manager.py:412-428`），**不存在 `save_config()`**。因此 `system.py:83` 调用必然抛 `AttributeError → 500`，该 POST 端点实际是坏的。
  2. `GET /api/settings` 同时在 `system.py:63` 与 `settings.py`（约 39 行）定义，`POST /api/settings` 在 `system.py` 与 `settings.py` 均存在 → 同路径多路由冲突，运行时「后者覆盖前者」行为隐式、易错。
- **改进建议**：收敛到单一 `settings.py` 负责配置读写；为 `ConfigManager` 补齐受控持久化方法（DB + 必要时的 YAML 基础设施段）；删除 `system.py` 中的重复 `/api/settings`。

### A-05（Medium）— 运行时重写 YAML 导致注释丢失与正则脆弱性
- **位置**：`core/config_manager.py:241-390`（`_normalize_yaml_file` 用模板字符串重写整个 `config.yaml`）；`core/config.py:116-123`（`ensure_security_config` 用正则改 `secret_key`）。
- **类别**：配置 / 健壮性
- **描述**：每次启动成功加载 DB 后都会用硬编码模板重写 `config.yaml`，**用户手写注释全部丢失**，且模板遗漏的字段（如 `monitor`、`retention_days` 等）可能被静默丢弃。`ensure_security_config` 用正则 `re.sub` 改写密钥，对 YAML 引号/多行/特殊字符敏感，存在破坏文件结构的风险。
- **改进建议**：YAML 采用「保留注释的结构化读写」（如 `ruamel.yaml`）；密钥轮换走专用加密存储，避免文件内正则改写。

### A-06（Medium）— 弱口令/弱密钥默认与薄弱检测
- **位置**：`core/config.py:111`（仅 4 个写死弱密钥字符串）；`core/config_manager.py:83`（默认口令 `password`）。
- **类别**：安全
- **描述**：默认管理员口令为 `password`，`ensure_security_config` 仅能识别 4 个硬编码弱 `secret_key` 字面量，其余任意弱值（如 `123456`、`admin`）均不会被轮换。无任何强制改密/强度校验。
- **改进建议**：启动时强制改密；口令强度策略；密钥使用 `secrets.token_urlsafe(32)` 且不在源码留默认值。

---

## 2. 分层与模块边界

### A-07（High）— 路由层混入业务逻辑与文件副作用
- **位置**：`app/routers/auth.py:51-69`（`update_profile` 正则+`yaml.safe_dump` 写文件）、`auth.py:148-163`（`change_password` 正则改写 `config.yaml`）；`app/routers/library.py:200`（`enrich_local_files_endpoint` 用 `asyncio.create_task` fire-and-forget）；`app/routers/wechat.py:169,173,379`（`background_download`/`background_add_artist` 用 `asyncio.create_task`）。
- **类别**：分层 / 可维护性
- **描述**：路由本应「薄」，却直接执行正则改写 YAML、触发无生命周期管理的后台任务。这使业务逻辑散落、无法单测，且文件写入与请求处理耦合（见 A-23 的后台任务风险）。
- **改进建议**：文件写入/密钥轮换/后台同步统一下沉到 services（如 `ConfigService`、`SyncOrchestrator`），路由只做参数校验与调用。

### A-08（High）— 服务层「上帝对象」
- **位置**：`app/services/scan_service.py`（**927 行**）；`app/services/library.py:206`（`LibraryService` Facade 注入 ArtistRefresh/Favorite/SongManagement/Scan/MetadataHealer/aggregator 等子服务）。
- **类别**：单一职责 / 可测试性
- **描述**：`scan_service.py` 同时承担本地扫描、元数据补全、去重、来源聚合、入库等多重职责，圈复杂度高、难以推理与单测；Facade 虽分解了子服务，但 `ScanService` 单体过大，成为维护瓶颈。
- **改进建议**：将 `scan_service.py` 按职责拆分为 `LocalScanner` / `MetadataEnricher` / `Deduplicator` / `Ingestor`，每个独立可测；Facade 仅做编排。

### A-09（Medium）— 路由职责重叠 / 重复定义
- **位置**：`app/routers/system.py:63` 与 `app/routers/settings.py`（~39）均定义 `GET /api/settings`；`app/routers/media.py`、`download.py`、`download_history.py` 对下载/播放/历史职责切分不清（见 `main.py:239-250` 注释显示 media/download 存在冗余）。
- **类别**：模块边界
- **描述**：同一资源（配置、下载）被多个路由模块瓜分，路由冲突与逻辑重复风险高，维护者难以定位「某个 API 到底在哪实现」。
- **改进建议**：按业务域（Config / Library / Download / Playback / Notification / Discovery）归一化到单一路由模块，消除跨模块同名路由。

### A-10（Medium）— 孤儿模块与不一致的 ORM 风格
- **位置**：`core/database.py:120`（`get_db()` 同步 `SessionLocal` 在 `main.py:37` 被 import 后基本未使用）；`app/domain/models.py`（`MediaInfo` 仅被 notifiers 使用）；`app/exceptions.py`（仅 `main.py` 消费）；`app/routers/.../pagination`（仅 library/download_history 使用）。
- **类别**：清晰度 / 整洁度
- **描述**：存在仅被单一处引用的「孤岛」模块与同步会话入口，增加认知负担；同时项目内 1.x 风格 `session.query(...)`（config_manager.py:181）与 2.0 `select()` 异步风格混用。
- **改进建议**：清理未使用入口；统一 ORM 风格为 2.0 `select()` + 异步会话；评估 `app/domain` 是否应提升为共享层。

### A-11（Low）— 遗留 `config` 字典仍在多处被引用
- **位置**：`app/routers/media.py:26`、`app/routers/system.py:24`、`core/security.py:7`（`from core.config import config`）。
- **类别**：技术债
- **描述**：虽 `core/config.py` 自称「Legacy Facade」，但仍有活跃引用（见 A-02、A-20），导致双源问题无法根除。
- **改进建议**：列入迁移清单，发布前全量移除。

---

## 3. 数据库层

### A-12（High）— 双重 Schema 初始化（create_all + Alembic）
- **位置**：`core/database.py:65-79`（`async_init_db` 先 `Base.metadata.create_all` 再 `await async_run_migrations()` 跑 Alembic head）。
- **类别**：数据库正确性
- **描述**：模型元数据建表与 Alembic 迁移重复执行。后果：(a) 若模型与迁移不一致，先 `create_all` 已建好表，后续迁移可能成为空操作或报错；(b) 产生「模型即真相 / 迁移即真相」的漂移隐患；(c) 新环境若模型领先迁移，旧迁移脚本形同虚设。
- **改进建议**：**二选一**——统一以 Alembic 为唯一建表来源（移除 `create_all`），或统一以模型为准并弃用迁移。推荐前者（保留 Alembic 便于演进），并在 CI 中加 `alembic check` 防漂移。

### A-13（High）— 同步/异步引擎混用与多实例碎片
- **位置**：`core/database.py:27,35-36`（`async_engine`/`AsyncSessionLocal`）；`database.py:82-95`（`sync_engine`/`SessionLocal`）；`database.py:97-118`（`init_db` 用 `ThreadPoolExecutor` 起新事件循环包 `async_init_db`）；`core/config_manager.py:174`（`_load_from_db` 自行 `create_engine(sync_database_url)` 新建独立引擎）。
- **类别**：并发 / 资源
- **描述**：
  1. `init_db()` 每次 new 一个 event loop + 线程池执行异步初始化，启动路径绕且易在复杂导入下踩坑。
  2. `ConfigManager._load_from_db` 在自己函数内 `create_engine` 建**第三个**引擎实例，与应用 `SessionLocal` 不是同一池——连接池碎片化、连接数不可控。
  3. 同步引擎（供 alembic、ConfigManager）与异步引擎并存，两套连接语义，排错困难。
- **改进建议**：统一会话入口；ConfigManager 复用应用 `sync_engine` 而非自建；`init_db` 改为在 lifespan 内直接 `await async_init_db()`（已是 async 上下文，无需线程池）。

### A-14（Medium）— SQLite 未启用 WAL，并发写锁风险
- **位置**：`core/database.py:27`（默认 `sqlite+aiosqlite:///config/music_monitor.db`，未配置 `PRAGMA journal_mode=WAL`）。
- **类别**：并发 / 可靠性
- **描述**：默认 rollback journal（`journal_mode=DELETE`）下，APScheduler 周期任务（新歌检查/完整性/自动缓存）、请求内写库、后台 `create_task` 任务可能并发写，触发「database is locked」。SQLite 单写者模型在异步并发场景尤为脆弱。
- **改进建议**：建库后执行 `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`；或将写入串行化到专用线程/队列；评估迁移至 Postgres（Docker 已预留 URL 格式）。

### A-15（Medium）— 配置加载即写入默认行 + 风格不一致
- **位置**：`core/config_manager.py:181-193`（`_load_from_db` 每次都 `session.add(new_settings); commit()` 若 `id=1` 不存在）。
- **类别**：数据库正确性
- **描述**：每次 `reload()` 若缺行便插入默认 `SystemSettings`，掩盖了「表未被迁移创建」的真实故障；同时此处用 1.x `session.query(SystemSettings).filter_by(id=1)` 风格，与项目 2.0 异步风格割裂。
- **改进建议**：默认行仅在首次安装向导中创建；用 2.0 `select()`；加载失败应明确告警而非静默补行。

### A-16（Low）— 仓储层分页去重查询可扩展性未验证
- **位置**：`app/repositories/song.py:177`（`get_paginated` 复杂去重查询）。
- **类别**：性能
- **描述**：去重 SQL 在大数据量下未经验证是否存在性能拐点；缺少必要索引评估。低优先级，建议在数据增长后做 `EXPLAIN` 复核。

---

## 4. 安全设计

### A-17（Critical）— 音频文件接口免鉴权开放
- **位置**：`main.py:281`（`path.startswith("/api/audio/")` 整体放行）；`app/routers/media.py:70-97`（`serve_audio` 无任何 `request.session` 校验）。
- **类别**：授权（AuthZ）
- **描述**：`/api/audio/{filename:path}` 被 `auth_middleware` 整段白名单放过，任何拿到 URL 的人（含分享链接、历史记录、日志泄露）均可下载全部音频文件。结合 `get_audio_path` 在多个目录模糊查找（media.py:78），文件名若可预测则构成直接资源泄露/版权风险。
- **改进建议**：音频下载改为「签名 URL + 会话校验」二选一；至少要求已登录会话；对 `{filename:path}` 做规范化防目录穿越（`os.path.realpath` 落在允许的媒体根下）。

### A-18（High）— 基于路径前缀的 allowlist 鉴权模型易漏配
- **位置**：`main.py:268-292`（`auth_middleware` 仅对 `/api/` 路径拦截，放行清单为硬编码列表）。
- **类别**：授权（AuthZ）
- **描述**：新增接口必须手动加入 `allowed_paths` 或前缀白名单，否则行为不可预期：未加入且不以特殊前缀开头的内部接口会被 401（可用性问题），而一旦误把内部接口前缀加入白名单即整体暴露。`test_notify_card`、`discovery/probe_qualities`、`discovery/cover` 等已被开放，新增端点极易被「忘记加白」或「误加白」。
- **改进建议**：改为**默认拒绝**——用 FastAPI 依赖 `Depends(require_auth)` 显式标注需鉴权端点；白名单仅保留真正的匿名端点（login/callback/health）。

### A-19（High）— 签名 URL TTL 过长且无重放防护
- **位置**：`core/security.py:30`（`generate_signed_url_params(ttl_seconds=259200)`，即 72 小时）；`security.py:54-82`（`verify_signature`）。
- **类别**：认证（AuthN）
- **描述**：移动端分享签名链接默认有效 3 天，窗口过长；签名仅绑定 `song_id|expires`，**无随机 nonce / 一次性消费**，同一 `sign` 在 TTL 内可无限次重放。
- **改进建议**：TTL 可配置且默认缩短（如 1 小时）；引入一次性 token 或已用签名记录（Redis/DB）防重放；对移动端接口同样要求会话或短期 JWT。

### A-20（Medium）— `get_secret_key` 取错配置键，密钥来源不一致
- **位置**：`core/security.py:20`（`config.get('global',{}).get('secret_key')`）；实际结构为 `auth.secret_key`（`config_manager.py:77`）。
- **类别**：安全 / 配置
- **描述**：`get_secret_key()` 先查 `config['global']['secret_key']`（结构错误，几乎必为 `None`），随后回退到 `ensure_security_config()` 从**文件**读取并改写——而 ConfigManager 持有的 `secret_key` 来自 DB/YAML。会话签名（SessionMiddleware 用 `ensure_security_config` 返回值，`main.py:295`）与 ConfigManager 可能持有不同密钥，产生「改了 YAML 后旧会话/旧签名仍有效」或「重启后密钥漂移」的隐患。
- **改进建议**：统一密钥唯一来源（`ConfigManager.get('auth.secret_key')`）；`security.py` 与 `main.py` 共用同一取值路径；文件回退仅在初始化阶段一次性发生。

### A-21（Medium）— 口令明文存储与明文比较
- **位置**：`app/routers/auth.py:26`（`req.password == auth_cfg.get('password')`）；`auth.py:139`（`req.old_password != auth_cfg.get('password')`）。
- **类别**：认证（AuthN） / 凭据保护
- **描述**：口令以明文存于 `config.yaml`，登录/改密用明文相等比较，无哈希（如 bcrypt/argon2）。一旦配置文件泄露，账号直接失陷；且明文口令经 A-03 的 `/api/settings` 回显进一步放大风险。
- **改进建议**：口令使用强哈希存储；登录/改密走 `verify()`；管理员口令初始化经安全引导流程。

### A-22（Low）— 企业微信回调验签链路复杂度
- **位置**：`app/routers/wechat.py`（多处的 `get_crypto` / `FixedWeChatCrypto`/`WeChatCrypto`）；`core/config_manager.py:220-223,375-377`（`corpid↔corp_id` 等键名反复互转）。
- **类别**：安全 / 可维护性
- **描述**：旧键名与新 snake_case 键在 YAML↔DB 迁移中来回转换，易在某一处遗漏导致验签取不到正确 key。低优先级但属潜在故障点。
- **改进建议**：确立单一键名规范（snake_case），迁移一次性固化，移除运行时双向转换。

---

## 5. 调度 / 事件总线 / WebSocket

### A-23（High）— Fire-and-forget 后台任务无生命周期管理
- **位置**：`app/routers/library.py:200`（`enrich_local_files_endpoint`）、`app/routers/wechat.py:169,173,379`（`background_download`/`background_add_artist`）、`app/services/...`（scan 触发）。
- **类别**：异步正确性 / 数据完整性
- **描述**：均用 `asyncio.create_task(...)` 派发后不持有句柄、不等待、不持久化。若客户端断开或进程在任务完成前退出（部署/重启/OOM），任务被取消且**无重试/无持久化队列**，导致「歌手已添加但未下载」「元数据补全丢失」等静默数据不完整。
- **改进建议**：改为经调度器（APScheduler `add_job`）或持久化任务队列（如 DB 任务表 + worker）执行；任务状态可观测、可重试、进程重启可恢复。

### A-24（Medium）— 事件总线缺少并发控制与错误处理
- **位置**：`core/event_bus.py:49-63`（`publish` 顺序遍历订阅者，同步/异步混调，单回调异常被吞）。
- **类别**：可靠性
- **描述**：`publish` 串行执行所有回调，一个慢速**同步**回调会阻塞事件循环；异常仅 `logger.error` 不中断其余订阅者但也无死信/重试；无背压。
- **改进建议**：对每个回调 `asyncio.create_task` + `try/except` 隔离；引入超时与失败计数；考虑结构化事件上下文。

### A-25（Medium）— WebSocket 连接管理器非线程安全
- **位置**：`core/websocket.py:9`（`active_connections: List[WebSocket]`）、`websocket.py:21-31`（`broadcast` 顺序 `send_json` 无锁）。
- **类别**：并发
- **描述**：`active_connections` 为裸 list，多个任务并发 `connect`/`disconnect`/`broadcast` 时存在竞态（如迭代中列表被改）。`broadcast` 逐条 `await send_json` 且单连接异常被静默 `pass`，可能掩盖连接已死的问题。
- **改进建议**：用 `asyncio.Lock` 保护列表，或改用 `set` + 在副本上迭代；对失效连接做清理而非吞异常；`disconnect` 改为 `async`。

### A-26（Medium）— 调度器启停缺乏优雅处理
- **位置**：`main.py:129,166`（`scheduler.start()` / `scheduler.shutdown(wait=False)`）；`app/routers/system.py:134`（`job_{source}` 引用）；`app/services/scheduling.py`（`register_recurring_jobs`）。
- **类别**：可靠性
- **描述**：`shutdown(wait=False)` 会立即中断正在运行的周期任务（如下载/扫描），可能造成半成品文件；`job_{source}` 依赖固定命名，若任务未注册则手动触发 404；auth 禁用时调度路径缺乏一致性保障。
- **改进建议**：`shutdown(wait=True)` 或显式 drain；用枚举/常量管理 job id；周期任务自身支持断点续做。

### A-27（Low）— 调度器单例与兜底路径不透明
- **位置**：`core/scheduler.py`（`SimpleScheduler` 包 `AsyncIOScheduler` 单例；`DummyScheduler` 兜底）。
- **类别**：健壮性
- **描述**：`DummyScheduler` 触发条件不清晰，若 `AsyncIOScheduler` 初始化失败会静默降级为无操作调度器，导致「任务看似注册实则从不执行」。
- **改进建议**：调度器初始化失败应**显式报错**而非静默降级；移除或明确记录 `DummyScheduler` 使用场景。

---

## 6. 可部署性

### A-28（High）— 依赖无版本锁定 + 本地 vendor wheel
- **位置**：`requirements.txt`（无 pin 版本；含 `./vendor/*.whl` 本地轮子）。
- **类别**：可重复构建 / 供应链
- **描述**：依赖未锁定精确版本，结合本地 `vendor` 轮子，构建结果随环境漂移，难以复现与审计；离线 `vendor` wheel 也可能与 PyPI 版本不一致。
- **改进建议**：生成 `requirements.lock`（或 `uv.lock`/`pip-tools`）；CI 中校验 hash；明确 `vendor` 用途与版本映射，或改为可信索引 + 构建缓存。

### A-29（Medium）— 镜像构建覆盖用户配置 / 权限处理脆弱
- **位置**：`Dockerfile`（多阶段；构建期 `cp config.example.yaml config.yaml`）；`scripts/entrypoint.sh`（`gosu`/`PUID` 权限处理 + `alembic upgrade head`）。
- **类别**：部署 / 配置可移植性
- **描述**：若 `config.yaml` 以镜像层而非卷挂载方式存在，构建期 copy 会覆盖用户配置；`entrypoint` 的 `PUID` 权限逻辑若与挂载卷属主不匹配，可能导致应用无写权限或 `alembic` 失败。权限降权与配置加载顺序耦合，排错困难。
- **改进建议**：配置一律走 volume，镜像内仅放 `config.example.yaml`；`entrypoint` 仅在配置文件缺失时从模板初始化；权限处理独立、可观测（启动前打印 uid/gid 与可写性检测）。

### A-30（Medium）— 开发与生产配置路径耦合
- **位置**：`config/config.yaml`（本地为 Windows 绝对路径 `D:/code/...`）；`core/config_manager.py:54-58`（`library_dir: /library` 等容器路径）；`core/config.py:78-82`（非 `/config` 时改写 `cache_dir`/`favorites_dir`）。
- **类别**：配置可移植性
- **描述**：本地 `config.yaml` 写死 Windows 绝对路径，与容器 `/config`、`/library` 体系不一致；迁移逻辑仅在「非 `/config`」时改写少量目录，环境切换依赖隐式分支，易在容器内部署时指向错误路径。
- **改进建议**：路径全部走相对/卷挂载 + 环境变量覆盖；消除「是否以 `/config` 开头」的隐式分支；提供 dev/prod 两套示例配置。

### A-31（Low）— 缺少健康检查端点
- **位置**：`main.py`（仅 SPA 回退；无 `/api/health`）；`docker-compose.yml`（无 `healthcheck` 证据）。
- **类别**：可运维性
- **描述**：容器编排（K8s/Docker）缺少探针端点，无法区分「进程在 but 依赖未就绪」。
- **改进建议**：新增 `GET /api/health` 返回 DB/调度器/通知通道状态；在 compose/K8s 配置探针。

### A-32（Low）— 优雅停机未考虑在途下载
- **位置**：`main.py:326`（`uvicorn.run(..., timeout_keep_alive=1)`）；`main.py:166`（`scheduler.shutdown(wait=False)`）。
- **类别**：可运维性
- **描述**：`timeout_keep_alive=1` 偏激进；在途大文件下载在停机时可能被截断。低优先级。
- **改进建议**：依据实际下载体量调整 keep-alive；停机前等待在途请求/任务完成。

---

## 7. 总体架构评估

**总体评价：B-（可用但技术债较重，安全与配置一致性是硬伤）**

系统分层骨架合理（routers / services / repositories / models 清晰），核心领域模型（Song / SongSource 核心-扩展模式、Artist、MediaRecord）设计得当，仓储基类泛型抽象恰当，迁移链完整（head = `9510064e9f42`）。但**工程质量被三处系统性问题拖累**：

1. **双配置源（A-02/A-03/A-20）** 是根因级技术债，贯穿配置、安全、模块边界，导致数据不一致与凭据泄露面。
2. **安全设计以「便利」优先**（A-17 音频免鉴权、A-18 前缀白名单、A-19 长 TTL、A-21 明文口令），在「内网自用」假设下尚可，一旦暴露即高危。
3. **异步任务生命周期缺失（A-23）** 与 **SQLite 并发模型（A-14）** 在规模化/重启频繁场景下会转化为数据不完整与锁故障。

架构方向正确，但需要一次「配置与鉴权一致性」专项重构，方能从「能跑」走向「可维护、可安全部署」。

---

## 8. Top 风险 / 优先级

| 优先级 | 编号 | 严重度 | 主题 | 一句话风险 |
|--------|------|--------|------|-----------|
| P0 | A-17 | Critical | 音频接口免鉴权 | 任意人可下载全部音频，版权/泄露 |
| P0 | A-01 | Critical | 明文密钥凭据 | 密钥/口令/企业微信凭证明文落盘 |
| P1 | A-02 | High | 双配置源不一致 | 网页改配置，测试/通知仍用旧值 |
| P1 | A-03 | High | 内部状态外泄 | `/api/settings` 回显明文 secret/口令 |
| P1 | A-12 | High | 双重建表 | 模型与迁移漂移，环境不可信 |
| P1 | A-13 | High | 引擎多实例 | 连接池碎片化、启动路径脆弱 |
| P1 | A-18 | High | 前缀白名单鉴权 | 新增端点易误暴露/误拦截 |
| P1 | A-19 | High | 签名 URL 72h | 分享链接重放窗口过长 |
| P1 | A-23 | High | 后台任务无生命周期 | 重启/断连致数据静默丢失 |
| P1 | A-28 | High | 依赖无锁版本 | 构建不可复现、供应链风险 |
| P1 | A-07 | High | 路由混业务逻辑 | 正则写文件+fire-forget，难测难维护 |
| P1 | A-08 | High | 服务上帝对象 | scan_service 927 行，维护瓶颈 |
| P2 | A-04/A-05/A-06/A-09/A-10/A-14/A-15/A-20/A-21/A-24/A-25/A-26/A-29/A-30 | 中 | 配置/DB/安全/异步/部署 | 见各条 |
| P3 | A-11/A-16/A-22/A-27/A-31/A-32 | 低 | 技术债/性能/可运维 | 清理与增强 |

**建议落地顺序**：先止血（P0：A-17 加鉴权、A-01 密钥外置）→ 再治本（P1：统一配置源 A-02/A-03/A-20、消除双重建表 A-12、统一引擎 A-13、默认拒绝鉴权 A-18、签名 TTL A-19、后台任务接管 A-23、依赖锁 A-28）→ 后清理（P2/P3 模块边界与可部署性增强）。

---

## 附录 A：与测试审查（`.review/03-testing.md`）的交叉印证

以下条目由 QA（严过关）在测试审查中发现、且属于本架构评审范围，经确认与本文 A-0X 结论**一致或互补**，特此交叉引用，避免两份报告结论冲突。QA 原始编号一并保留以便对照。

### C-01（安全 / 白名单）— 鉴权放行清单的额外暴露面（印证 A-17、A-18）
- **QA 编号**：Q-27，位置 `main.py:281`。
- **补充事实**：除 `/api/audio/` 前缀整段放行（即 A-17）外，`/api/test_notify_card` 为**测试端点暴露在生产**（任何人均可触发企业微信推送，可作骚扰放大器）；`/api/discovery/probe_qualities`、`/api/discovery/cover` 会触发对外部音乐平台的请求，存在 SSRF / 流量放大风险。
- **需拍板的架构决策**：建议 `/api/audio/` 改用签名 URL（HMAC + 过期，与 A-19 同机制）；`/api/test_notify_card` 以环境变量限定仅 dev；discovery 端点加来源校验/速率限制。白名单增删须有测试固化（QA 主张「测试即文档」）。

### C-02（可测试性 / 单例）— 全局惰性单例阻碍测试与可替换性（互补 A-08、A-13）
- **QA 编号**：Q-12，位置 `app/services/_singletons.py`（`get_aggregator()` / `get_download_service()`）、`new_release_monitor.py:199-206`、`task_monitor` 模块级实例。
- **说明**：`global _x is None` 惰性单例在测试中无法打掉已缓存实例——先跑用例触发真实构造后，后续用例会拿到含真实 provider 的实例（可能发真外网请求）；`scan_service.py:123` 的 `task_monitor.start_task()` 在进程级单例留永不结束的 task 记录，污染后续用例。
- **与 A-13 方向一致**：建议统一改为 FastAPI `Depends` 注入，测试用 `dependency_overrides` 替换；新增依赖勿再加全局单例（呼应 C-04）。

### C-03（健壮性 / 异常吞噬）— 具体编码错误被静默降级（强化 A-10）
- **QA 编号**：Q-23 根因，位置 `app/routers/auth.py:216`（使用**未导入**的 `select`）+ `auth.py:242` 裸 `except Exception: logger.warning`。
- **实证**：`/api/profile_stats` 调用 `select(func.count(...))` 时 `select` 未导入 → `NameError`，被函数内 `try/except` 吞掉，端点仍返回 HTTP 200 + 全 0 数据。**此具体 bug 为 QA 动态测试发现；本文静态审查（A-10）仅指出「静默失败」模式、未单独点出该实例，特此补记并致谢 QA。**
- **系统性根因**：`app/utils/error_handler.py` 的 `@handle_service_errors(fallback_value=, raise_on_critical=False)` 将 `NameError` / `AttributeError` 等必现编码错误降级为静默数据错误。
- **建议**：区分「业务可恢复异常」与「程序错误」——后者 fail-fast，或至少 `logger.exception()` 带堆栈；dev/test 环境经环境变量强制重抛。

### C-04（可测试性正面）— `get_async_session` 是干净的依赖样板（印证 A-13 方向）
- **QA 指出**：`core/database.py:128` 的 `get_async_session` 为标准 async generator dependency，API 层测试可零改造接入（`app.dependency_overrides[get_async_session]`）。这是当前架构可测试性最好的一处，建议新依赖统一此模式（与 A-13「统一会话入口」一致）。

### C-05（配置治理）— pytest 双配置冲突（归入 A-02 同类）
- **QA 指出**：`pytest.ini` 与 `pyproject.toml [tool.pytest.ini_options]` 双份冲突（pytest.ini 优先、pyproject 被静默忽略）。这与 `core/config_manager.py` 的 YAML + DB 混合配置同属「多事实源」问题，归入 A-02 配置治理范畴一并治理。

> **交叉结论**：QA 测试审查与本架构评审在「鉴权白名单」（A-17/A-18）、「双配置源」（A-02）、「单例/会话入口」（A-08/A-13）、「静默失败」（A-10）上**相互印证、无冲突**；QA 另以动态测试补出 `auth.py:216` 的具体 swallowed-bug（C-03），已并入本附录。两份报告可合并阅读，无需修订 A-0X 编号。

---

*报告结束。所有结论均基于 `D:\code\music-monitor` 实际源码阅读，未改动任何文件。*
