# music-monitor 测试质量独立审查报告

| 项目 | 内容 |
|---|---|
| 审查对象 | `D:\code\music-monitor`（FastAPI + SQLAlchemy 2.0 async + APScheduler + SQLite / Vue3） |
| 审查范围 | `tests/`、`测试/`、`pytest.ini`、`pyproject.toml`、`.github/workflows/`、`app/**`、`core/**`、`main.py` |
| 审查人 | 严过关（QA 工程师，软件开发团队） |
| 审查方式 | 只读静态审查 + git 历史取证 + `.pytest_cache` 取证 + 逻辑离线复现（未修改任何源码/测试） |
| 审查日期 | 2026-03-10 |
| 结论评级 | **测试成熟度 Level 1-（Initial / 事实上无回归网）** |

---

## 执行摘要

一句话结论：**这个项目当前没有可用的回归安全网。** 后端约 15,000 行 Python、27 个 service、14 个 router，自动化测试只剩 **9 个测试函数**（其中 1 个函数体是 `pass`，实际有效 8 个），估算行覆盖率 **≈ 3%**；`测试/` 目录下看似"专业"的 23 个用例中，绝大多数是 **mock 完对象再断言 mock 自己**，一行生产代码都没执行，是**负资产级的虚假信心**。

三个最关键的事实：

1. **测试是被删掉的，不是没写过。** `.pytest_cache/v/cache/nodeids` 记录了 **180 个历史测试节点**，`lastfailed` 记录了 **49 个失败用例**。git 取证显示 commit `f7bd209` 一次性删除了 `tests/services/test_favorite_service.py`、`test_song_management_service.py`、`test_smart_merger.py`、`test_artist_refresh_service.py`、`tests/test_backend_health.py`、`tests/test_pagination.py` 等**真实单元测试文件**，与约 50 个 debug 脚本一起被"大扫除"。被删的文件里有 22 个用例正处于 failing 状态——**这是用删除测试来"修复"红灯**，属于最严重的工程治理问题。
2. **测试缺失已经在放行真实缺陷。** 我在本次只读审查中即定位到 4 个已在主干上的运行时缺陷：`app/routers/auth.py:216` 使用了**未导入的 `select`**（`/api/profile_stats` 永远静默返回 0）；去重服务把 `'test'` 当作伴奏关键词做**子串匹配**（"Greatest Hits"、"Protest"、"Contest"、"The Latest" 全被误判为伴奏）；连字符正则把 "A-Ha" 截成 "a"；`_pick_best_song` 存在**循环变量泄漏到循环外使用**。这些全部落在"本该有单测"的纯函数上。
3. **CI 不跑测试。** `.github/workflows/` 只有 `docker-publish.yml`，PR 只构建镜像不执行 pytest；`requirements.txt` 里**连 pytest 都没有**，任何人在干净环境都无法复现测试。

本报告给出 **28 条结构化发现（Q-01 ~ Q-28）**：Critical 6 条、High 12 条、Medium 8 条、Low 2 条；并附**覆盖率矩阵**与**分阶段可落地补测清单**（含可直接复制的 conftest / CI / mock 代码）。

---

## 一、覆盖率映射矩阵

### 1.1 现存自动化测试全清单

`pytest.ini` 生效配置为 `testpaths = tests`，因此**实际会被执行的只有 `tests/` 下 3 个文件**：

| 测试文件 | 用例数 | 有效性 | 被测目标 |
|---|---|---|---|
| `tests/test_services/test_deduplication_service.py` | 3 | ✅ 真实执行生产代码 | `DeduplicationService._normalize_title` / `_pick_best_song` / `deduplicate_songs` |
| `tests/test_services/test_new_release_monitor.py` | 2 | ✅ 质量最高的一组（真 DB + 假 provider） | `NewReleaseMonitorService.check_artist` |
| `tests/test_services/test_scan_service.py` | 4 | ⚠️ 其中 1 个为空测试 | `ScanService._normalize_cn_brackets` / `scan_local_files`(空目录) / `_find_or_create_song` |
| **合计** | **9** | **有效 8** | — |

> `测试/` 目录（7 个文件，23 个用例）**未被 `pytest.ini` 的 testpaths 包含，常态下一次都不会执行**（详见 Q-10、Q-18）。

### 1.2 Service 层覆盖矩阵（27 个模块）

图例：✅ 有自动化测试｜🟡 仅部分方法/仅手工方案｜❌ 零测试

| # | Service 模块 | LOC | 自动化测试 | 说明 |
|---|---|---:|:---:|---|
| 1 | `deduplication_service.py` | 349 | ✅ 部分 | 3 用例，仅覆盖 happy path，**未覆盖已存在的 3 个缺陷** |
| 2 | `new_release_monitor.py` | 206 | ✅ 较好 | 2 用例，覆盖发现+去重复通知；缺失败/异常分支 |
| 3 | `scan_service.py` | 927 | 🟡 极少 | 仅 3 个方法被触及，`_extract_metadata`/`_analyze_quality`/`_prune_missing_files` 全裸奔 |
| 4 | `artist_refresh_service.py` | 753 | ❌ | **曾有 9 个用例，已被删除** |
| 5 | `metadata_service.py` | 727 | ❌ | 仅 `测试/` 手工方案引用（不执行） |
| 6 | `download_service.py` | 696 | ❌ | **P0 核心链路，含限流器 `TokenBucket`、音质探测、断点下载** |
| 7 | `song_management_service.py` | 663 | ❌ | **曾有 16 个用例，已被删除**（删除歌曲/歌手、重下载） |
| 8 | `metadata_healer.py` | 641 | ❌ | 仅 `测试/` 手工方案引用 |
| 9 | `media_service.py` | 438 | ❌ | 播放/路径修复 |
| 10 | `music_providers/aggregator.py` | 397 | ❌ | 仅在 new_release 测试中被 Fake 替换，本体零覆盖 |
| 11 | `tag_service.py` | 338 | ❌ | 音频标签写入，涉及文件破坏风险 |
| 12 | `music_providers/qqmusic_provider.py` | 333 | ❌ | 外部 API |
| 13 | `subscription.py` | 285 | ❌ | **P0，歌手订阅/智能关联/删除** |
| 14 | `smart_merger.py` | 281 | ❌ | **曾有 23 个用例，已被删除**；现仅 `测试/验收测试` 里 4 行断言 |
| 15 | `notification.py` | 275 | ❌ | **P0，会真实外发企业微信** |
| 16 | `history_service.py` | 254 | ❌ | |
| 17 | `library.py` | 206 | ❌ | |
| 18 | `music_providers/netease_provider.py` | 194 | ❌ | 外部 API |
| 19 | `music_providers/base.py` | 193 | ❌ | `async_retry` 重试装饰器，**重试语义无测试** |
| 20 | `task_monitor.py` | 181 | ❌ | 全局单例，被 scan 测试隐式污染 |
| 21 | `favorite_service.py` | 175 | ❌ | **曾有 9 个用例，已被删除**；含移动文件的破坏性操作 |
| 22 | `wechat_download_service.py` | 158 | ❌ | |
| 23 | `download_history_service.py` | 113 | ❌ | |
| 24 | `scheduling.py` | 108 | ❌ | APScheduler 调度注册 |
| 25 | `auto_download_service.py` | 108 | ❌ | 仅在 new_release 测试中被 Fake 替换 |
| 26 | `wechat_session_service.py` | 59 | ❌ | 会话过期语义无测试 |
| 27 | `_singletons.py` | 49 | ❌ | 单例工厂，测试无 reset 机制 |

**Service 覆盖率：2.5 / 27 ≈ 9%（按模块）；按语句估算 < 5%。**

### 1.3 Router / API 层覆盖矩阵（14 个模块）

| # | Router | LOC | 自动化测试 | 风险备注 |
|---|---|---:|:---:|---|
| 1 | `library.py` | 475 | ❌ | 最大路由，资料库 CRUD |
| 2 | `wechat.py` | 389 | ❌ | **回调验签 / 解密 / 指令分发全裸奔（Critical）** |
| 3 | `system.py` | 276 | ❌ | 系统操作 |
| 4 | `auth.py` | 245 | ❌ | **登录/改密/改资料/头像上传全裸奔；且已含 NameError 缺陷（Q-23）** |
| 5 | `media.py` | 233 | ❌ | 播放/下载入口 |
| 6 | `settings.py` | 226 | ❌ | **设置持久化（写 YAML + DB）无回归保护** |
| 7 | `discovery.py` | 212 | ❌ | 部分端点被 auth 中间件放行 |
| 8 | `subscription.py` | 190 | ❌ | |
| 9 | `metadata.py` | 102 | ❌ | |
| 10 | `download_history.py` | 101 | ❌ | |
| 11 | `download.py` | 99 | ❌ | |
| 12 | `task_control.py` | 19 | ❌ | |
| 13 | `websocket.py` | 18 | ❌ | |
| 14 | `version.py` | 12 | ❌ | |

**Router 覆盖率：0 / 14 = 0%。整个 HTTP 层、鉴权中间件、异常处理器、依赖注入链路无任何自动化验证。**

### 1.4 其他层

| 层 | 模块数 | 覆盖 | 备注 |
|---|---:|:---:|---|
| `app/repositories/` | 4 | 0 | `SongRepository.toggle_favorite` 等仅被间接触及 |
| `app/notifiers/` | 3 | 0 | `wecom.py` 252 行，**无 dry-run 开关** |
| `app/utils/` | 2 | 0 | `error_handler.py` 的 `@handle_service_errors` 吞异常语义无测试（放大 Q-23 类缺陷） |
| `core/` | 9 | 0 | `config_manager.py` 463 行、`security.py`、`wechat.py`(FixedWeChatCrypto) 全无测试 |
| `app/models/` | 8 | 0 | 仅 `Base.metadata.create_all` 被间接执行；**Alembic 迁移无测试** |
| `main.py` | 1 | 0 | 鉴权中间件、异常处理器、SPA 回退无测试 |

### 1.5 任务清单中点名模块的对照结论

| 关键模块 | 是否有测试 | 严重度 |
|---|:---:|---|
| auth 登录 / 改密 / 改资料 | ❌ 无 | **Critical** |
| download 下载链路 | ❌ 无 | **Critical** |
| favorite 收藏（含文件移动） | ❌ 无（曾有 9 个，被删） | **Critical** |
| scan 扫描 | 🟡 3/16 方法 | High |
| new_release_monitor 监控 | ✅ 基本覆盖 | — |
| notification 通知 | ❌ 无 | **Critical** |
| wechat 回调验签 | ❌ 无 | **Critical** |
| metadata 元数据 | ❌ 无（仅不执行的手工方案） | High |
| subscription 订阅 | ❌ 无 | High |
| settings 持久化 | ❌ 无 | High |

---

## 二、结构化发现（Q-01 ~ Q-28）

### A 类：覆盖率与工程治理

---

#### Q-01 ｜Critical｜自动化测试覆盖率仅约 3%，与后端体量严重失配
**位置**：`tests/`（全目录，3 文件 / 9 用例）vs `app/`（约 15,000 行）

**问题描述**：后端已实现 27 个 service（9,172 行）、14 个 router（2,616 行）、9 个 core 模块（1,312 行），但自动化测试仅 9 个函数、约 250 行。按被执行语句粗估行覆盖率 **≈ 3%**，模块覆盖率 **≈ 4%（3/68）**。这意味着任何一次重构、依赖升级、Bug 修复都**没有任何自动信号**告诉你是否打断了别的功能，回归完全依赖人肉。

**可落地改进建议**：
1. 立即接入 `pytest-cov` 并把当前真实数字写进 README 作为基线（`pytest --cov=app --cov=core --cov-report=term-missing`）。
2. 采用**棘轮（ratchet）策略**而非一次性冲高：CI 门槛设为"当前值 + 不允许下降"，每个 PR 要求新增/改动文件的 patch coverage ≥ 70%（`diff-cover` 或 `pytest-cov` + `--cov-fail-under`）。
3. 按本报告 §3 的 P0 清单，用 4 个迭代把 service 层拉到 45%、router 层拉到 60%。

---

#### Q-02 ｜Critical｜历史测试套件被批量删除，且删除的多是当时正在失败的用例
**位置**：commit `f7bd209`；证据 `.pytest_cache/v/cache/nodeids`（180 节点）、`.pytest_cache/v/cache/lastfailed`（49 节点）

**问题描述**：`.pytest_cache` 保留了历史执行快照，与当前文件系统比对结果如下：

| 历史测试文件 | 历史用例数 | 当前存在 | 曾失败数 |
|---|---:|:---:|---:|
| `tests/services/test_smart_merger.py` | 23 | ❌ 已删 | 0 |
| `tests/services/test_song_management_service.py` | 16 | ❌ 已删 | 13 |
| `tests/services/test_favorite_service.py` | 9 | ❌ 已删 | 6 |
| `tests/services/test_artist_refresh_service.py` | 9 | ❌ 已删 | 2 |
| `tests/test_backend_health.py` | 3 | ❌ 已删 | 2 |
| `tests/services/test_metadata_service_refactor.py` | 2 | ❌ 已删 | 0 |
| `tests/services/test_enrichment_logic.py` | 1 | ❌ 已删 | 1 |
| `tests/test_pagination.py` | — | ❌ 已删 | 1 |
| `测试/后端/歌手监控/test_artist_monitoring.py` | 13 | ❌ 已删 | 13 |
| `测试/后端/元数据补全/test_metadata_completion.py` | 11 | ❌ 已删 | 6 |
| `测试/test_config_manager.py` | 15 | ❌ 已删 | 0 |
| `测试/test_plugin_manager.py` | 14 | ❌ 已删 | 0 |
| `测试/test_event_bus.py` | 11 | ❌ 已删 | 0 |
| `测试/frontend_api/*.py` | 9 | ❌ 已删 | 0 |
| `测试/后端/test_framework_verification.py` | 4 | ❌ 已删 | 0 |
| **合计消失** | **约 140** | | **44** |

`git log --diff-filter=D` 确认这些文件在 `f7bd209`（"重构并新增大量后端服务…"）中与约 50 个 `debug_*.py` / `verify_*.py` / `fix_*.py` 脚本被**一起清理掉了**。问题在于：debug 脚本该删，**`tests/services/test_*.py` 是正规单元测试，不该删**；而且其中 44 个是当时的红灯用例——**删除失败测试等同于把已知缺陷藏起来**。

**可落地改进建议**：
1. 从 `f7bd209^` 恢复这 4 个单测文件到一个 `tests/legacy/` 目录：
   `git show f7bd209^:tests/services/test_smart_merger.py > tests/test_services/test_smart_merger.py`（其余同理）。
2. 逐个跑，把**真实产品缺陷**导致的失败开 issue 修生产代码；把**接口已重构**导致的失败改断言；**任何情况下不得删除测试来变绿**。`test_smart_merger.py`（23 用例，历史 0 失败）应当能几乎零成本复活——这是性价比最高的一步。
3. 在 `CONTRIBUTING`/团队规约中写死红线：**删除测试文件必须在 PR 描述中说明理由并单独 commit**，禁止与功能改动混提。

---

#### Q-03 ｜Critical｜HTTP/API 层 100% 无测试，鉴权与微信回调裸奔
**位置**：`app/routers/*.py`（14 文件 2,616 行）、`main.py:268-292`（auth 中间件）

**问题描述**：没有任何一个 API 端点有自动化测试。这直接导致：路由注册漏挂（`main.py:239/249` 已有两处被注释掉的 `include_router`，无人验证是否漏了端点）、鉴权中间件白名单错误、请求/响应 schema 变更、依赖注入断链——全部无法在提交时发现。`main.py:281` 的 `path.startswith("/api/audio/")` 白名单尤其危险（见 Q-27）。

**可落地改进建议**：
项目已有干净的注入点 `core.database.get_async_session`（`core/database.py:128`，标准 async generator dependency），**可以零改造地做 API 测试**：

```python
# tests/conftest.py 追加
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from core.database import get_async_session

@pytest_asyncio.fixture
async def api_client(db_session, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from main import app
    async def _override():
        yield db_session
    app.dependency_overrides[get_async_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

优先补：`/api/login`（正确/错误密码/鉴权关闭三态）、`/api/change_password`、`/api/check_auth`、`/api/wecom/callback` GET+POST、`/api/settings` 读写往返。

---

### B 类：测试可靠性与正确性

---

#### Q-04 ｜High｜`event_loop` fixture 在当前 pytest-asyncio 版本下已失效（deprecated / removed）
**位置**：`tests/conftest.py:11-16`

```python
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

**问题描述**：重定义 `event_loop` fixture 是 pytest-asyncio ≤0.21 的老写法。自 **0.23 起被标记 deprecated**，**1.0 起被彻底移除**——重定义不再被插件识别，它退化成一个"没人用的普通 fixture"。而 `.pytest_cache` 中的 `.pyc` 文件名显示本项目最近使用的是 **pytest 9.0.2 / 9.0.3（Python 3.13）**，该版本只能搭配 pytest-asyncio ≥1.x。也就是说**这段代码目前是死代码，且给读者传递了"事件循环已被正确管理"的错误印象**。此外 `asyncio.get_event_loop_policy()` 在 Python 3.12+ 亦已 deprecated。

**可落地改进建议**：删除 `event_loop` fixture，改用 pytest-asyncio 1.x 官方机制：
```ini
# pytest.ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
```
并在需要更宽循环作用域的 fixture 上显式声明 `@pytest_asyncio.fixture(loop_scope="session")`。

---

#### Q-05 ｜High｜session 作用域异步 fixture 与 function 作用域事件循环冲突
**位置**：`tests/conftest.py:18-24`（`test_engine`，`scope="session"`）与 `:26-34`（`db_session`，function scope）

**问题描述**：`test_engine` 是 **session 作用域的 async fixture**，但在 pytest-asyncio 1.x 下 async fixture 的默认 **loop_scope 是 function**。一个在 A 循环里创建的 aiosqlite 连接，被 B 循环里的 `db_session` 使用，典型症状就是 `RuntimeError: ... attached to a different loop` 或 `MissingGreenlet`。这一点**已被项目自己实锤**——`tests/test_services/test_new_release_monitor.py:64` 的注释白纸黑字写着：

> `"""在每个测试自己的事件循环里跑，避免 pytest-asyncio 循环错位导致 MissingGreenlet。"""`

也就是说开发者遇到了这个问题，但没修 conftest，而是**绕开 conftest 另起炉灶**（见 Q-07）。

**可落地改进建议**：见 Q-06 给出的完整重写版 conftest；核心是 `@pytest_asyncio.fixture(loop_scope="session", scope="session")` 成对声明，或干脆把 engine 降为 function 作用域（内存库建表成本极低，实测毫秒级）。

---

#### Q-06 ｜High｜`db_session` 的 rollback 隔离不可靠，测试间存在数据泄漏
**位置**：`tests/conftest.py:26-34`

**问题描述**：这里有两个需要分开说清楚的事实：

1. **关于"`:memory:` 每个连接是独立库"**：对 `sqlite+aiosqlite:///:memory:`，SQLAlchemy 的 aiosqlite 方言会自动选用 **`StaticPool`**（`get_pool_class` 对 memory 库返回 StaticPool），因此**同一个 engine 内的所有 session 共享同一条物理连接、同一个内存库**。所以任务书中的猜测"每个 test 拿到全新空库"**不成立**——建表确实生效，fixture 数据确实共享。
2. **但正因为共享，rollback 隔离才是假的**：`db_session` 在 yield 后只做 `await session.rollback()`，这只能回滚**当前 session 中尚未提交**的工作。而被测代码大量自行 `commit()`——例如 `favorite_service.py:136` `await db.commit()`、`new_release_monitor.py:132` `await db.commit()`、`scan_service` 批量提交。**一旦被测代码 commit，rollback 无效，数据永久留在 session 级共享的内存库里，泄漏给后续所有测试**。

当前只有 9 个用例、彼此数据不冲突，所以还没炸；一旦补测到几十个用例，就会出现"单跑绿、全跑红"的经典幽灵故障。

**可落地改进建议**：改用 **"外层事务 + SAVEPOINT 嵌套"** 的标准隔离模式，让被测代码的 `commit()` 只提交到 savepoint，teardown 时整体回滚：

```python
# tests/conftest.py（推荐重写版）
import pytest, pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,          # 显式声明，别依赖方言默认
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(loop_scope="session")
async def db_session(test_engine) -> AsyncSession:
    """外层事务 + SAVEPOINT：被测代码的 commit() 只落到 savepoint，用例结束整体回滚。"""
    conn = await test_engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()
```
> `join_transaction_mode="create_savepoint"` 是 SQLAlchemy 2.0 提供的官方写法，比手写 `after_transaction_end` 事件监听器干净得多。项目已依赖 `SQLAlchemy>=2.0.30`，可直接使用。

---

#### Q-07 ｜High｜三套并存的 DB 搭建方式，测试基础设施事实性分裂
**位置**：`tests/conftest.py`（方式 A）、`tests/test_services/test_new_release_monitor.py:63-73`（方式 B）、`tests/test_services/test_deduplication_service.py`（方式 C：纯 Mock 类，不用 DB）

**问题描述**：
- 方式 B 在同步测试函数里手搓 `asyncio.run()` + 自建 engine + 自建 sessionmaker + 自己 `create_all`，**完全绕过 conftest**。
- 方式 C 在测试文件内定义了 3 套各不相同的 `MockSong` / `MockSource` / `MockArtist` 局部类（`test_deduplication_service.py:18-36`、`:50-64`），字段还不一致（一个有 `publish_time`，一个没有）。

后果：fixture 零复用、mock 对象与真实 ORM 模型漂移无人察觉（比如 `MockSong` 缺 `cover` 字段，恰好让 `_pick_best_song` 的封面分支静默跳过）、新人不知道该抄哪套、修 conftest 修不动实际问题。

**可落地改进建议**：
1. 统一到 Q-06 的 `db_session`，删除 `run_in_memory` 手搓循环（前提是先修好 Q-04/Q-05，否则它确实跑不起来）。
2. 建立 `tests/factories.py` 集中放置领域对象工厂（推荐 `factory_boy` 或简单的 `dataclass` 构造函数），替代散落各处的局部 Mock 类：
```python
# tests/factories.py
def make_song(db, *, title="Song", artist=None, local_path=None, status="PENDING", **kw): ...
def make_artist(db, *, name="测试歌手", is_monitored=True, sources=(), **kw): ...
def make_song_info(**kw): ...   # 供 provider 层复用
```
3. 若坚持要用 Mock 替身，改用 `unittest.mock.create_autospec(Song, instance=True)`，模型字段变更时会自动报错。

---

#### Q-08 ｜High｜存在空测试，函数体是 `pass`，永远通过
**位置**：`tests/test_services/test_scan_service.py:26-40`

```python
async def test_extract_metadata_fallback(db_session):
    service = ScanService()
    with patch("app.services.scan_service.ScanService._extract_metadata") as mock_extract:
        mock_extract.return_value = {...}
        # We're testing the logic that uses this metadata
        # Since we don't want to touch the real filesystem, we mock the scan loop
        pass
```

**问题描述**：这个测试**什么都没断言、什么都没调用**，patch 完就 `pass`。它在测试报告里贡献一个"PASSED"，是纯粹的**覆盖率与信心污染**。9 个用例里有 1 个是假的，占 11%。同文件还有 `import os` / `MagicMock` 未使用（PEP8 F401）。

**可落地改进建议**：要么删掉，要么用 `pytest.mark.skip(reason="TODO: 待补 _extract_metadata 回退逻辑")` 显式标注为待办（这样在报告里显示为 skipped 而非 passed），要么补完真实断言：
```python
async def test_extract_metadata_fallback_from_filename(tmp_path):
    """无内嵌标签时，应从文件名 '歌手 - 标题.mp3' 回退解析。"""
    f = tmp_path / "周杰伦 - 稻香.mp3"; f.write_bytes(b"\x00" * 1024)
    meta = await ScanService()._extract_metadata(str(f), f.name)
    assert meta["title"] == "稻香"
    assert meta["artist_name"] == "周杰伦"
```

---

#### Q-09 ｜High｜测试依赖完全未声明，干净环境无法复现
**位置**：`requirements.txt`（35 行，0 个测试依赖）、`pyproject.toml:8-18`（dependencies 亦无）

**问题描述**：`requirements.txt` 里没有 `pytest`、`pytest-asyncio`、`pytest-cov`、`pytest-mock`；`测试/后端/性能测试/test_performance.py:9` 直接 `import psutil`，而 psutil **不在任何依赖清单里**——这个文件在干净环境必然 `ModuleNotFoundError` 而 collect error。我在本机验证：`python -c "import pytest"` → `ModuleNotFoundError: No module named 'pytest'`，即**当前环境根本装不上/没装测试栈**，"测试能跑"这件事从未被环境固化。

**可落地改进建议**：新建 `requirements-dev.txt` 并在 CI 中安装：
```
-r requirements.txt
pytest>=8.3,<10
pytest-asyncio>=1.0
pytest-cov>=5.0
pytest-mock>=3.14
respx>=0.21          # httpx 的 HTTP mock
aioresponses>=0.7    # aiohttp 的 HTTP mock（本项目 aiohttp/httpx 并用）
freezegun>=1.5       # 时间相关（last_notified_at / 会话过期）
factory-boy>=3.3
psutil>=6.0          # 若保留性能测试
```
或在 `pyproject.toml` 增加 `[project.optional-dependencies] dev = [...]`。注意 `pytest-asyncio` 与 `pytest` 的版本需成对锁定，避免 Q-04 类问题复发。

---

#### Q-10 ｜High｜`pytest.ini` 与 `pyproject.toml` 双份冲突配置，后者被静默忽略
**位置**：`pytest.ini:1-9` vs `pyproject.toml:30-42`

| 配置项 | `pytest.ini`（**生效**） | `pyproject.toml`（**被忽略**） |
|---|---|---|
| `testpaths` | `tests` | `["测试", "tests"]` |
| `addopts` | `-v --tb=short` | `--strict-markers --tb=short` |
| `asyncio_mode` | `auto` | `auto` |

**问题描述**：pytest 的配置文件优先级为 `pytest.ini` > `pyproject.toml`，且**不合并**。因此：
- `测试/` 目录**永远不会被收集**（开发者可能以为它在跑）；
- `--strict-markers` 未生效，`@pytest.mark.asyncio` 之外的拼错 marker 不会报错；
- 两份文件长期漂移，谁改哪份全靠猜。

**可落地改进建议**：**删除 `pytest.ini`**，只保留 `pyproject.toml` 单一事实源（项目已用 pyproject 管依赖）：
```toml
[tool.pytest.ini_options]
minversion = "8.0"
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]
addopts = "-v --tb=short --strict-markers --strict-config -p no:randomly"
markers = [
  "unit: 纯函数/无 IO 单元测试",
  "integration: 需要 DB 或 ASGI 客户端",
  "external: 需要真实外网（默认 deselect）",
  "slow: 耗时 > 1s",
]
filterwarnings = ["error::DeprecationWarning:app.*"]
```
`测试/` 的处置见 Q-18。

---

#### Q-11 ｜Medium｜根目录 `test_api.py` 是命名地雷，一旦被收集即 collect error
**位置**：`/test_api.py:8`

```python
async def test_api_call(artist_id):     # ← pytest 会当成测试，artist_id 被当作 fixture
    async with AsyncSessionLocal() as db:   # ← 连真实 config/music_monitor.db
```

**问题描述**：文件名匹配 `test_*.py`，函数名匹配 `test_*`，参数 `artist_id` 会被 pytest 当成 fixture 请求 → `fixture 'artist_id' not found`。当前靠 `testpaths=tests` 侥幸躲过；但只要有人执行 `pytest`（带路径参数）、或按 `pyproject.toml` 的意图恢复 testpaths、或 IDE 全量发现，立刻红。而且它**连的是生产 SQLite 库**（`AsyncSessionLocal` → `config/music_monitor.db`），属于诊断脚本而非测试。

**可落地改进建议**：移动并改名为 `scripts/diagnose_artist_detail.py`（`scripts/` 目录已存在），与 Q-02 中删掉的那批 debug 脚本归位到同一处。

---

#### Q-12 ｜Medium｜全局单例 / lru_cache 状态跨用例泄漏，形成隐性顺序依赖
**位置**：`app/services/task_monitor.py`（模块级 `task_monitor` 单例）、`app/services/_singletons.py:1-49`、`app/services/deduplication_service.py:10-11`（`@staticmethod @functools.lru_cache(maxsize=4096)`）、`app/services/new_release_monitor.py:199-206`（`_service` 全局）

**问题描述**：
- `test_scan_local_files_empty` 会调用真实的 `task_monitor.start_task("scan", ...)`（`scan_service.py:123`），在**进程级全局单例**里留下一个永不结束的 task 记录，污染后续所有用例；且无任何 reset fixture。
- `DeduplicationService._normalize_title` 的 `lru_cache` 是进程级的，缓存内容跨用例存活。若将来对归一化规则做参数化测试（比如验证 Q-24 的修复），旧缓存会让断言产生假绿/假红。
- `get_aggregator()` / `get_new_release_monitor()` / `get_auto_download_service()` 都是 `global _x is None` 惰性单例，`test_new_release_monitor.py` 用 monkeypatch 打掉了工厂函数，但**没打掉已缓存的实例**——若某个先跑的用例触发过真实构造，后跑的用例会拿到真 Aggregator（内含真 provider，可能发真请求）。

**可落地改进建议**：加一个 autouse 的隔离 fixture：
```python
# tests/conftest.py
@pytest.fixture(autouse=True)
def _isolate_global_state():
    from app.services import _singletons, new_release_monitor as nr
    from app.services.deduplication_service import DeduplicationService
    from app.services.task_monitor import task_monitor
    DeduplicationService._normalize_title.cache_clear()
    yield
    DeduplicationService._normalize_title.cache_clear()
    for mod, attr in [(_singletons, "_aggregator"), (_singletons, "_download_service"), (nr, "_service")]:
        if hasattr(mod, attr):
            setattr(mod, attr, None)
    getattr(task_monitor, "tasks", {}).clear()
```
更根本的做法是把单例改成 FastAPI 依赖注入（`Depends(get_aggregator)`），测试用 `dependency_overrides` 替换——这条建议应与架构评审同步。

---

#### Q-13 ｜Medium｜并发执行（pytest-xdist）不安全
**位置**：`tests/`（整体设计）

**问题描述**：由于 ① 共享 session 级内存库（Q-06）、② 进程级全局单例（Q-12）、③ `测试/` 系列会写真实文件系统与配置文件、④ 没有任何 `tmp_path` 隔离约定，当前套件**无法安全地 `pytest -n auto`**。9 个用例还感受不到，补到几百个用例后串行执行时间会成为 CI 瓶颈。

**可落地改进建议**：从一开始就按 xdist 兼容来设计——engine/DB 采用 function 作用域或按 worker 分库（`f"sqlite+aiosqlite:///:memory:?worker={os.getenv('PYTEST_XDIST_WORKER','main')}"`）；所有文件操作强制走 `tmp_path` fixture；配置读写通过 monkeypatch 指向 `tmp_path/config.yaml`。在 P1 阶段引入 `pytest-xdist` 并在 CI 跑 `-n auto` 以尽早暴露顺序依赖。

---

#### Q-14 ｜Medium｜断言充分性不足、无参数化、异常路径零覆盖
**位置**：`tests/test_services/test_deduplication_service.py:4-15`、`tests/test_services/test_new_release_monitor.py`

**问题描述**：
- `test_normalize_title` 用 7 条硬编码 `assert` 串在一个函数里：**第一条失败后面全不执行**，且失败信息看不出是哪个输入挂了。更关键的是这 7 条**全是精心挑选的 happy path**，完全避开了 Q-24/Q-25 那两类真实缺陷。
- `test_pick_best_song_logic` 只断言了 `id`/`available_sources`/`status` 三个字段，而 `_pick_best_song` 返回 **16 个字段**；`quality` 计算（60 行逻辑）、`local_files` 收集、`publish_time` 合并（含 Q-26 缺陷）、`cover` 优先级全部无断言。
- `new_release_monitor` 只测了成功路径。provider 抛异常（`new_release_monitor.py:80-82`）、通知失败（`:187-188`）、入队失败（`:194-195`）这三个**显式写了 try/except 的分支**——恰恰是最需要测试的地方——一个都没覆盖。
- 全套件 **0 处 `pytest.mark.parametrize`**、**0 处 `pytest.raises`**。

**可落地改进建议**：
```python
@pytest.mark.parametrize("raw,expected", [
    ("Song Name", "song name"),
    ("Song (Live)", "song"),
    ("Another [2023 Remix]", "another"),
    ("Title | Subtitle", "title"),
    ("Track (Instrumental)", "track_inst"),
    ("Song (伴奏)", "song_inst"),
    # —— 回归用例：以下为 Q-24 / Q-25 缺陷，修复前 xfail ——
    pytest.param("Greatest Hits", "greatest hits", marks=pytest.mark.xfail(reason="Q-24 'test' 子串误判")),
    pytest.param("A-Ha", "a-ha", marks=pytest.mark.xfail(reason="Q-25 连字符过度截断")),
    ("", ""), (None, ""),
])
def test_normalize_title(raw, expected):
    assert DeduplicationService._normalize_title(raw) == expected
```
异常路径示例：
```python
async def test_check_artist_survives_provider_error(monkeypatch, db_session):
    """provider 抛异常时应记录日志并继续，不中断整体检查。"""
    ...
    assert await service.check_artist(db_session, artist) == 0
    assert notified == []           # 不应误发通知
```

---

### C 类：`测试/` 手工方案的价值与成本

---

#### Q-15 ｜Critical｜`测试/` 下用例大量"自 mock 自断言"，未执行任何生产代码
**位置**：`测试/后端/API连接/test_api_integration.py:42-87`、`测试/后端/性能测试/test_performance.py:65-136`、`测试/后端/验收测试/test_acceptance.py:16-105`

**问题描述**：这是本次审查发现的**最具误导性**的问题。典型样本（`test_api_integration.py:43-65`）：

```python
async def test_metadata_api_integration(self):
    with patch('app.services.metadata_service.MetadataService') as mock_service_class:
        mock_service = Mock()
        mock_service.get_best_match_metadata = AsyncMock(return_value=mock_result)
        result = await mock_service.get_best_match_metadata("测试歌曲", "测试歌手")   # ← 调的是 Mock
        assert result.success is True                                              # ← 断言 Mock 的返回值
```

它 patch 掉 `MetadataService`，然后**调用自己造的 Mock、断言自己设的返回值**——`app/services/metadata_service.py` 的 727 行代码**一行都没被执行**。这本质上是在测试 `unittest.mock` 库本身，永远绿。同类问题遍布：

| 用例 | 位置 | 实际被测对象 |
|---|---|---|
| `test_metadata_api_integration` | `test_api_integration.py:43` | Mock |
| `test_music_provider_integration` | `test_api_integration.py:68` | Mock |
| `test_response_time_monitoring` | `test_api_integration.py:102` | `time.sleep(0.01) < 5000ms` |
| `test_concurrent_requests_handling` | `test_api_integration.py:123` | 线程池本身 |
| `test_metadata_search_performance` | `test_performance.py:66` | Mock 的调用耗时 |
| `test_concurrent_search_performance` | `test_performance.py:98` | `asyncio.gather` 本身 |
| `test_database_connection_pooling` | `test_performance.py:141` | Mock 工厂调用计数 |
| `test_high_concurrency_load` | `test_performance.py:217` | 线程 + Mock 构造 |
| `test_complete_music_workflow` | `test_acceptance.py:17` | Mock |
| `test_batch_processing_scenario` | `test_acceptance.py:62` | Mock |
| `test_graceful_failure_recovery` | `test_acceptance.py:111` | 断言 Mock 抛出自己设的异常 |
| `test_configuration_loading` | `test_acceptance.py:154` | 断言 Mock 返回自己设的 dict |
| `test_logging_system` | `test_acceptance.py:169` | `logging` 标准库 |
| `test_database_operations` | `test_acceptance.py:183` | Mock |
| `test_response_format_consistency` | `test_acceptance.py:209` | 断言测试自己写的字面量 dict |
| `test_error_messages_clarity` | `test_acceptance.py:230` | 断言测试自己写的中文串含"请"字 |

`test_acceptance.py:209-243` 尤其荒谬——它定义一个 dict 然后断言这个 dict 里有自己刚写进去的 key。**23 个用例里只有 `test_acceptance.py:132-149`（`SmartMerger.is_garbage_value` / `is_invalid_date`，4 行断言）真正碰到了生产代码。**

**可落地改进建议**：
1. **删除** `test_performance.py`（全部）、`test_api_integration.py` 的 `TestPerformanceMetrics`、`test_acceptance.py` 的 `TestUserExperience` / `TestSystemIntegration.test_logging_system` / `test_configuration_loading` / `test_database_operations`。保留它们的唯一效果就是掩盖真实覆盖率。
2. 抢救有价值的部分：`test_acceptance.py:132-149` 的 SmartMerger 断言，合并回从 `f7bd209^` 恢复的 `tests/test_services/test_smart_merger.py`（Q-02）。
3. 在团队规约中写死判据：**"如果把被测模块整个删掉，测试仍然通过，那它就不是测试。"** Code review 时对任何 `patch(...)` 后紧跟着调用同一个 mock 的代码直接打回。

---

#### Q-16 ｜High｜API 断言接受 404，端点被删也能通过
**位置**：`测试/后端/API连接/test_api_integration.py:33`、`:40`

```python
response = client.get("/api/system/health")
assert response.status_code in [200, 401, 404]   # 200/401/404 全接受
```

**问题描述**：`404` 意味着"路由不存在"。这条断言的实际含义是"只要服务器还能返回 HTTP 响应就算通过"，连**端点被误删、路由未注册、路径拼错**都发现不了。考虑到 `main.py:239/249` 确实存在被注释掉的 `include_router`，这类断言的失效风险是真实的。

**可落地改进建议**：断言必须精确到状态码与关键字段：
```python
def test_health_endpoint_returns_ok(api_client_no_auth):
    r = api_client_no_auth.get("/api/system/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_protected_endpoint_requires_login(api_client_auth_enabled):
    r = api_client_auth_enabled.get("/api/library/songs")
    assert r.status_code == 401           # 明确断言鉴权生效，不接受 404
```
鉴权开关应通过 monkeypatch `get_config_manager()` 显式控制成两个 fixture，而不是用"或"断言掩盖不确定性。

---

#### Q-17 ｜High｜性能测试使用机器相关的绝对阈值，天生 flaky
**位置**：`测试/后端/性能测试/test_performance.py:42-43`、`:59-60`、`:94-95`、`:136`、`:268`

```python
assert current_memory < 500      # 进程 RSS < 500MB —— 与机器/解释器版本强相关
assert current_cpu < 90          # 全局 CPU 使用率 < 90% —— 与并行任务强相关
assert total_time < 5.0          # 挂钟时间 —— CI runner 抖动即失败
```

**问题描述**：这些阈值依赖**宿主机当时的负载**。在 GitHub Actions 共享 runner 上，`psutil.cpu_percent()` 完全可能瞬时超过 90%（尤其配合 `pytest -n auto`）；`total_time` 类断言在冷启动/IO 抖动下随机红灯。**Flaky 测试比没有测试更糟**——它会训练团队养成"红了就 re-run"的习惯，最终对所有红灯脱敏。叠加 Q-09（psutil 未声明依赖），这个文件在 CI 里必然出问题。

**可落地改进建议**：
1. 性能测试**移出功能 CI**，单独打 `@pytest.mark.slow` 或 `@pytest.mark.benchmark`，默认 `-m "not slow"` 排除。
2. 如需性能守护，改用 `pytest-benchmark` 的**相对基线比较**（对比历史 median，回退超过 X% 才失败），而非绝对秒数。
3. 真正值得做的性能测试是**算法复杂度回归**——例如 `DeduplicationService.deduplicate_songs` 在 10k 首歌下的耗时、`scan_local_files` 的 N+1 查询次数（用 SQLAlchemy 事件计数 SQL 条数并断言上界）。这类断言与机器无关，才有回归价值。

---

#### Q-18 ｜Medium｜`测试/` 永不执行，但测试报告声称"28 个用例通过"
**位置**：`pytest.ini:3`（`testpaths = tests`）、`测试/后端/元数据补全/测试结果/元数据补全功能测试报告.md:19-46`

**问题描述**：报告声称覆盖"元数据补全 7 + API 集成 7 + 性能 5 + 验收 9"共 28 个用例并通过。但：① `测试/` 不在生效的 testpaths 内，常态执行 `pytest` 根本不收集它；② 报告所依据的 `test_metadata_completion.py`（11 用例，其中 6 个 failing）**已经不存在**；③ 剩下的 23 个用例中 19 个是 Q-15 所述的自 mock 断言。**这份报告目前提供的是纯粹的虚假保证**，比没有报告危害更大——它会让人误判"元数据补全已验证"。

**可落地改进建议**：
1. 明确 `测试/` 的定位为「**人工探索性测试方案与历史报告归档**」，在目录下加 `README.md` 声明"本目录不参与 CI，不代表自动化覆盖"。
2. 把 `.py` 文件里**唯一有价值的那部分**（`test_metadata_healing.py` 中 `TestKeywordPreprocessing` / `TestProgressiveSearchStrategy` 确实调用了真实的 `MetadataService._preprocess_search_keywords` / `_exact_search`，我已核对这些方法在 `metadata_service.py:66/602/609/616` 仍然存在）**迁移到 `tests/test_services/test_metadata_service.py`**，纳入 CI。
3. 历史测试报告 `.md` 加上"数据已过期，仅供追溯"的注记，或移入 `需求/审查报告存档`。

---

#### Q-19 ｜Medium｜测试方案文档与代码脱节
**位置**：`测试/后端/元数据补全/测试方案.md`（302 行）、`测试/后端/音频下载测试方案.md`（17 行）

**问题描述**：`测试方案.md` 有 302 行详细设计，但它对应的执行体 `test_metadata_completion.py` 已被删除；`音频下载测试方案.md` 只有 17 行且**没有任何对应的测试代码**（`download_service.py` 696 行，0 覆盖）。文档描述的是"应该测什么"，现实是"什么都没测"，这个 gap 无人管理。

**可落地改进建议**：把 `音频下载测试方案.md` 的 17 行要点**直接翻译成 P0 的 `tests/test_services/test_download_service.py` 用例骨架**（先写 `@pytest.mark.skip` 的空壳 + 明确的 docstring），让文档与代码在同一个文件里对齐。方案文档的价值在于「转成可执行用例」，而不是长期停留在 `.md`。

---

### D 类：外部依赖与 Mock 策略

---

#### Q-20 ｜High｜缺少 HTTP 层 mock 基建，provider / aggregator / 下载链路无法离线测试
**位置**：`app/services/music_providers/*.py`（1,117 行）、`app/services/download_service.py:208-478`、`app/services/metadata_service.py`

**问题描述**：项目同时使用 `aiohttp>=3.9.5` 和 `httpx>=0.27.0` 两套 HTTP 客户端，外加 `pyncm`（vendored wheel）和 `qqmusic-api-python` 两个第三方 SDK。**没有引入任何 HTTP mock 库**，导致：
- 想测 provider 就必须联网访问网易云/QQ音乐 → 慢、不稳定、可能触发风控/限流。
- `test_new_release_monitor.py` 只能靠自己写 `FakeProvider`/`FakeAggregator` 类 + monkeypatch 绕过（能用，但每写一个新测试都要重造轮子，且绕过了 aggregator 的真实聚合/去重/校验逻辑，`aggregator.py` 397 行仍是 0 覆盖）。
- `download_service.py` 的 `TokenBucket` 限流（`:88-144`）、`_probe_single_quality`（`:324`）、`download_file` 断点续传（`:419`）这些**纯逻辑 + IO 混合**的关键代码完全无法验证。

**可落地改进建议**：分三层建立 mock 策略——

| 层级 | 被测对象 | Mock 手段 |
|---|---|---|
| L1 网络边界 | httpx 调用（metadata/download） | **`respx`**：`respx.get("https://...").mock(return_value=httpx.Response(200, json=FIXTURE))` |
| L1 网络边界 | aiohttp 调用 | **`aioresponses`**：`with aioresponses() as m: m.get(url, payload=FIXTURE)` |
| L2 SDK 边界 | `pyncm` / `qqmusic-api` | `monkeypatch.setattr(netease_provider, "cloudsearch", fake)`，用**录制的真实响应 JSON** 存 `tests/fixtures/netease_search.json` |
| L3 服务边界 | provider → aggregator 以上 | 保留现有 `FakeProvider` 模式，但抽到 `tests/fakes.py` 共享 |

关键原则：**fixture JSON 必须是从真实 API 录制的**（可写一个 `scripts/record_fixtures.py` 一次性抓取并脱敏），否则 mock 与真实契约漂移。另外补一组 `@pytest.mark.external` 的**契约测试**（每天定时跑一次，不阻塞 PR），用于及时发现上游 API 变更：
```python
@pytest.mark.external
async def test_netease_search_contract_still_valid():
    """每日定时跑：验证录制的 fixture 结构仍与真实 API 一致。"""
```

---

#### Q-21 ｜Medium｜通知与下载副作用无注入点，测试有真实外发风险
**位置**：`app/notifiers/wecom.py`（252 行）、`app/services/notification.py:74-275`（全 `@classmethod`）、`app/services/favorite_service.py:128-132`（`shutil.move` 真实移动文件）

**问题描述**：
- `NotificationService` 全部是 classmethod + 模块级配置读取（`notification.py:26-37`），要 mock 只能像 `test_new_release_monitor.py:47-49` 那样 `monkeypatch.setattr(NotificationService, "notify_new_song", classmethod(stub))`——侵入且脆弱。**没有全局 dry-run 开关**，意味着任何人不小心跑了未 mock 的测试就会**向真实企业微信群发消息**。
- `FavoriteService.toggle` 会真的 `shutil.move` 文件（`:128`）。历史上被删除的 `test_favorite_service.py` 有 9 个用例正是覆盖这部分（其中 6 个 failing），现在这段**具有破坏性的文件操作**零保护。

**可落地改进建议**：
1. 增加环境变量级熔断（生产代码改动很小，收益很大）：
```python
# app/services/notification.py
import os
_DRY_RUN = os.getenv("MM_NOTIFY_DRY_RUN", "").lower() in ("1", "true")
# 在每个发送方法入口：
if _DRY_RUN:
    logger.info(f"[DRY-RUN] 抑制外发: {snapshot}"); return True
```
并在 `tests/conftest.py` 里 autouse 地 `monkeypatch.setenv("MM_NOTIFY_DRY_RUN", "1")`——**默认安全**。
2. 文件操作测试统一用 `tmp_path`，并 monkeypatch `get_config_manager()` 让 `cache_dir`/`favorites_dir`/`library_dir` 全部指向 `tmp_path` 子目录。恢复 `test_favorite_service.py` 时按此改造。

---

### E 类：CI / 流水线

---

#### Q-22 ｜Critical｜CI 不执行任何测试，PR 无质量门禁
**位置**：`.github/workflows/docker-publish.yml`（唯一的 workflow）

**问题描述**：该 workflow 在 `push` 到 main 和 `pull_request` 时触发，但内容只有：checkout → 校验 tag 与 `version.py` 一致 → buildx → 登录 registry → build & push。**没有 `pip install`，没有 `pytest`，没有 lint，没有覆盖率**。也就是说：一个把 9 个测试全改成 `assert False` 的 PR 也能顺利合并并发布镜像。这是 Q-01/Q-02 得以发生的**制度性根因**——没有门禁，测试腐化就是必然。

**可落地改进建议**：新增 `.github/workflows/test.yml`：

```yaml
name: Tests
on:
  pull_request:
  push:
    branches: [main]

jobs:
  pytest:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.13"]   # 生产 Docker 用哪个就必须包含哪个
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - name: Install deps
        run: |
          python -m pip install -U pip
          pip install -r requirements.txt -r requirements-dev.txt
      - name: Lint (non-blocking at first)
        run: ruff check app core tests || true
      - name: Run tests
        env:
          MM_NOTIFY_DRY_RUN: "1"
          DATABASE_URL: "sqlite+aiosqlite:///:memory:"
        run: |
          pytest -m "not external and not slow" \
                 --cov=app --cov=core \
                 --cov-report=xml --cov-report=term-missing \
                 --cov-fail-under=${{ vars.COV_MIN || 3 }} \
                 --junitxml=junit.xml -n auto
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results-${{ matrix.python-version }}, path: junit.xml }
```
配套：
- 把 `docker-publish.yml` 的 build job 加 `needs: pytest`，**测试不过不出镜像**。
- 在 GitHub 仓库设置里把 `pytest` 设为 **required status check**，并开启"删除测试文件需 review"的 CODEOWNERS 规则覆盖 `tests/`。
- `COV_MIN` 用 repository variable 管理，每个迭代手动上调（棘轮），初值设为当前真实值（约 3），第 1 迭代 → 20，第 2 → 35，第 3 → 45。

---

### F 类：因测试缺失而放行的真实运行时缺陷（测试价值的实证）

> 以下 6 条不是"测试写得不好"，而是"**因为没有测试，这些缺陷此刻正躺在主干上**"。它们全部落在纯函数或简单分支上，属于单元测试的射程范围内，**任何一条基础用例都能拦住**。

---

#### Q-23 ｜Critical｜`/api/profile_stats` 使用未导入的 `select`，永远静默返回 0
**位置**：`app/routers/auth.py:216`、`:221`（`select` 未导入）；`:204` 只导入了 `func`

```python
@router.get("/api/profile_stats")
async def profile_stats(db: AsyncSession = Depends(get_async_session)):
    from sqlalchemy import func            # ← 只导入了 func
    ...
    try:
        stmt_artist = select(func.count(Artist.id))    # ← NameError: name 'select' is not defined
        ...
    except Exception as e:
        logger.warning(f"获取统计信息失败: {e}")        # ← 异常被吞
    return stats     # ← 永远返回 {"artist_count": 0, "song_count": 0, "cache_size": "0 MB"}
```

**问题描述**：我已用 grep 核实：`auth.py` 全文只有 `from sqlalchemy.ext.asyncio import AsyncSession`（第 3 行），**从未导入 `select`**。因此第 216 行必然抛 `NameError`。而它被包在一个宽泛的 `except Exception` 里只打 warning 日志，所以**接口 HTTP 200、前端个人中心永远显示 0 歌手 / 0 歌曲 / 0 MB 缓存**，用户看到的是"功能坏了但不报错"。对比其他文件（如 `wechat.py:364` 的 `from sqlalchemy import select`）可知这是遗漏。

**可落地改进建议**：
1. 生产修复：`auth.py:204` 改为 `from sqlalchemy import func, select`。
2. 回归测试（P0）：
```python
async def test_profile_stats_returns_real_counts(api_client, db_session):
    db_session.add(Artist(name="A")); db_session.add(Song(title="S", unique_key="k1"))
    await db_session.flush()
    r = await api_client.get("/api/profile_stats")
    assert r.status_code == 200
    assert r.json()["artist_count"] == 1     # 修复前这里是 0 → 测试会红
    assert r.json()["song_count"] == 1
```
3. **系统性建议**：审查 `app/utils/error_handler.py` 的 `@handle_service_errors` 与各处裸 `except Exception`。这类"吞掉一切"的写法把 `NameError`/`AttributeError` 这种**必现的编码错误**降级成了静默数据错误，是本条缺陷能长期存活的根本原因。建议至少让 `except Exception` 分支 `logger.exception()`（带堆栈）而非 `logger.warning(e)`，并在开发/测试环境通过环境变量强制重新抛出。同时引入 `ruff`（规则 `F821 undefined-name`）——**这个缺陷 ruff 静态扫描 1 秒内就能发现**。

---

#### Q-24 ｜High｜去重服务把 `'test'` 当伴奏关键词且用子串匹配，大量正常歌曲被误判
**位置**：`app/services/deduplication_service.py:23`

```python
inst_markers = ['test', 'instrumental', 'inst.', '伴奏', 'karaoke', 'off vocal']
for m in inst_markers:
    if m in t:          # ← 子串匹配
        is_inst = True
```

**问题描述**：`'test'` 显然是调试时留下的临时标记，忘记删除。更糟的是这里用的是**子串匹配**，导致任何包含 "test" 字母序列的标题都被打上 `_inst` 后缀。我已离线复现（纯逻辑复刻，未导入项目）：

| 输入 | 实际输出 | 期望输出 |
|---|---|---|
| `Greatest Hits` | `greatest hits_inst` ❌ | `greatest hits` |
| `Protest Song` | `protest song_inst` ❌ | `protest song` |
| `The Latest` | `the latest_inst` ❌ | `the latest` |
| `Contest` | `contest_inst` ❌ | `contest` |

后果：这些歌曲的原版与其它来源版本**永远无法合并去重**，在资料库里持续显示为重复条目；`Greatest Hits` 是英文专辑/合辑的高频词，影响面不小。

**可落地改进建议**：
1. 生产修复：删除 `'test'`；并把子串匹配改为**词边界匹配**：
```python
_INST_RE = re.compile(r'(?:\b(instrumental|inst\.?|karaoke|off\s*vocal)\b|伴奏|纯音乐)', re.I)
is_inst = bool(_INST_RE.search(t))
```
2. 回归测试：见 Q-14 给出的 parametrize 版本（已包含 `Greatest Hits` 用例）。

---

#### Q-25 ｜High｜连字符正则过度截断，`A-Ha` → `a`，造成错误合并
**位置**：`app/services/deduplication_service.py:37`

```python
t_clean = re.sub(r'[\||－|-].*$', '', t_clean)
```

**问题描述**：这个字符类里 `|` 被重复写了三次（字符类内 `|` 是字面量，写法本身就有问题），效果是"遇到 `|`、`－`、`-` 就把后面全砍掉"。离线复现：

| 输入 | 实际输出 | 风险 |
|---|---|---|
| `Title - CD1` | `title` | ✅ 符合意图 |
| `A-Ha` | `a` | ❌ 乐队名被砍 |
| `Rock-n-Roll` | `rock` | ❌ 歌名被砍 |
| `Jay-Z` | `jay` | ❌ |
| `Twenty-One Pilots` | `twenty` | ❌ |

所有以 `a` 开头被砍剩 `a` 的标题会**互相合并成同一首歌**——这是数据破坏级的去重误判。

**可落地改进建议**：
1. 生产修复：只在连字符**两侧有空格**时才视为分隔符，且只剥离已知的尾缀模式：
```python
t_clean = re.sub(r'\s+[|｜]\s*.*$', '', t_clean)                     # 竖线分隔
t_clean = re.sub(r'\s+[-－—]\s+(cd\s*\d+|disc\s*\d+|.*版)\s*$', '', t_clean, flags=re.I)
```
2. 回归测试：参数化加入 `A-Ha`、`Jay-Z`、`Rock-n-Roll`、`Title - CD1` 四组对照。

---

#### Q-26 ｜High｜`_pick_best_song` 循环变量泄漏到循环外使用，publish_time 合并逻辑失效
**位置**：`app/services/deduplication_service.py:280-295`

```python
for item in group:                                  # ← 循环 A（第 280 行）
    cv = getattr(item, 'cover', None)
    if cv and cv.startswith("/uploads/"):
        final_dict['cover'] = cv
        break                                       # ← 可能提前 break

# 发布时间补全 (QQ 优先逻辑)
pt = getattr(item, 'publish_time', None)            # ← 第 287 行：循环外用 item！
if pt:
    item_source_names = [s.source for s in item_sources]   # ← item_sources 泄漏自第 215 行的循环 B
    if 'qqmusic' in item_source_names:
        best_publish_time = pt
    elif not best_publish_time:
        best_publish_time = pt
```

**问题描述**：第 287-293 行的这段"发布时间补全"**看起来应该在循环里遍历整个 group**，但它写在循环外面，实际只作用于 `item` 的最后一次绑定值——而这个值取决于循环 A 是正常跑完（= group 最后一个元素）还是提前 `break`（= 第一个有 `/uploads/` 封面的元素）。更隐蔽的是 `item_sources`（第 289 行）根本不属于循环 A，它泄漏自 **73 行之前的循环 B**（第 215 行 `item_sources = getattr(item, 'sources', [])`），此时 `item_sources` 对应的是循环 B 的最后一个元素——**两个变量指向不同对象，逻辑完全错乱**。

结果：多来源合并时，"QQ 音乐发布时间优先"这条业务规则**基本不生效**，实际取到哪个时间是随机的（取决于 group 顺序和封面分布）。

**可落地改进建议**：
1. 生产修复：把这段逻辑收进一个显式循环，并去掉对泄漏变量的依赖：
```python
for it in group:
    pt = getattr(it, 'publish_time', None)
    if not pt:
        continue
    srcs = [s.source for s in getattr(it, 'sources', [])]
    if 'qqmusic' in srcs:
        best_publish_time = pt        # QQ 优先，直接覆盖
        break
    if not best_publish_time:
        best_publish_time = pt
```
2. 回归测试：构造一个 group，其中 netease 版 `publish_time="2020-01-01"`、qqmusic 版 `="2019-05-05"`，断言 `result["publish_time"] == "2019-05-05"`。同时构造一个"第一个元素有 `/uploads/` 封面"的场景，验证 break 不影响时间选取。
3. **系统性建议**：`ruff` 的 `B023`/`PLW2901` 与 `pylint` 的 `undefined-loop-variable (W0631)` 能直接扫出这类问题。这是把 lint 接入 CI 的又一个理由。

---

#### Q-27 ｜Medium｜鉴权中间件对 `/api/audio/` 前缀完全放行，未登录可拉取音频流
**位置**：`main.py:281`

```python
if path in allowed_paths or path.startswith("/api/test_notify_card") or path.startswith("/api/audio/"):
    pass    # 放行，不校验 session
```

**问题描述**：`/api/audio/` 是**前缀匹配**且不做任何 token 校验，意味着开启鉴权后，未登录者只要知道/枚举出资源路径就能直接下载音频。同样被无条件放行的还有 `/api/test_notify_card`（**测试端点上生产**，任何人可触发企业微信推送，可被用作骚扰放大器）和 `/api/discovery/probe_qualities`、`/api/discovery/cover`（会触发对外部音乐平台的请求，可被用作 SSRF/流量放大）。这些白名单条目**没有任何测试覆盖，也没有注释说明为何必须放行**。

**可落地改进建议**：
1. 与架构评审同步该风险。若 `/api/audio/` 放行是为了让 `<audio>` 标签能播放（cookie 通常是能带上的，除非跨域），应改为**签名 URL**（HMAC + 过期时间）而非整段放行；`/api/test_notify_card` 应用环境变量开关限制为仅 dev 可用。
2. 回归测试（P0，安全类）：
```python
@pytest.mark.parametrize("path", [
    "/api/library/songs", "/api/settings", "/api/profile_stats",
    "/api/subscription/artists", "/api/download/history",
])
async def test_protected_endpoints_reject_anonymous(api_client_auth_enabled, path):
    assert (await api_client_auth_enabled.get(path)).status_code == 401

async def test_audio_endpoint_is_intentionally_public(api_client_auth_enabled):
    """白名单必须被测试固化：改动白名单就要改这个测试，强制人做决策。"""
    r = await api_client_auth_enabled.get("/api/audio/1")
    assert r.status_code != 401
```
把白名单写成**测试即文档**，任何人增删白名单都必须同步修改测试，避免悄悄放行。

---

#### Q-28 ｜Medium｜微信指令分发存在 fall-through 与会话未清理，无任何测试
**位置**：`app/routers/wechat.py:157-208`

**问题描述**：
1. **fall-through**：第 158-180 行处理数字指令。若 session 存在、`idx` 合法，但 `stype` 既不是 `'song'` 也不是 `'artist'`（脏数据/未来新增类型），代码会走到第 176 行 `clear_db_session` 然后**不 return，继续往下走到第 205 行把数字当关键词去搜歌**——用户输入 "3" 会得到"搜索『3』的结果"，行为诡异。
2. **死代码 / 会话泄漏**：第 176 行的 `await WeChatSessionService.clear_db_session(user_id)` 位于 `if/elif` 两个 `return` **之后**，正常路径永远执行不到。这意味着用户选完一次之后**会话不会被清理**，仍在有效期内，重复发同一个数字会重复触发下载。
3. **验签路径零测试**：`get_crypto()`（第 43-70 行）有三层配置回退（`notify.wecom` → `notifications.providers.wecom`，`encoding_aes_key`/`aes_key`，`corpid`/`corp_id`）和一个 `FixedWeChatCrypto` → `WeChatCrypto` 的降级 fallback。这段逻辑分支很密、且是**安全边界**（验签失败必须 403），却一个测试都没有。第 85 行的 `except InvalidSignatureException` 在 `HAS_WECHATPY=False` 时是未定义名（虽然被上面的 `if not crypto: return 500` 挡住，但属于脆弱耦合）。

**可落地改进建议**：
1. 生产修复：数字分支加 `else: return "⚠️ 会话数据异常，请重新搜索"`；把 `clear_db_session` 移到 `create_task` 之前。
2. 回归测试（P0）——这部分**完全可以离线测**，`dispatch_command` 是纯 async 函数，只需 mock `WeChatSessionService` 和 `aggregator`：
```python
@pytest.mark.parametrize("content,expect_kw", [
    ("帮助", "Music Monitor 助手"), ("help", "Music Monitor 助手"),
])
async def test_help_command(content, expect_kw):
    assert expect_kw in await dispatch_command(content, "u1")

async def test_digit_without_session_returns_expired(monkeypatch):
    monkeypatch.setattr(WeChatSessionService, "get_db_session", AsyncMock(return_value=None))
    assert "会话已过期" in await dispatch_command("1", "u1")

async def test_digit_out_of_range(monkeypatch):
    monkeypatch.setattr(WeChatSessionService, "get_db_session",
                        AsyncMock(return_value={"type": "song", "results": [{"title": "A"}]}))
    assert "有效的序号" in await dispatch_command("5", "u1")

@pytest.mark.parametrize("content,intent,kw", [
    ("歌手 周杰伦", "artist", "周杰伦"), ("下载 稻香", "song", "稻香"),
    ("周杰伦", "song", "周杰伦"), ("歌手", None, "请输入关键词"),
])
async def test_intent_parsing(content, intent, kw): ...
```
验签测试用 `wechatpy` 自己的加解密造样本，断言：签名正确 → 200 + 回显；签名错误 → **403**；配置缺失 → 500。

---

## 三、可落地测试策略与优先级清单

### 3.1 第 0 步：先把地基修好（0.5 人日，必须最先做）

| # | 动作 | 对应发现 |
|---|---|---|
| 0-1 | 删除 `pytest.ini`，配置统一到 `pyproject.toml`（含 marker 体系） | Q-10 |
| 0-2 | 重写 `tests/conftest.py`：去掉 `event_loop`，改 SAVEPOINT 隔离，加 `loop_scope="session"` | Q-04/05/06 |
| 0-3 | 新增 `requirements-dev.txt` | Q-09 |
| 0-4 | 加 `_isolate_global_state` autouse fixture + `MM_NOTIFY_DRY_RUN=1` 默认值 | Q-12/Q-21 |
| 0-5 | `test_api.py` 移到 `scripts/`；删除 `test_extract_metadata_fallback` 空测试 | Q-11/Q-08 |
| 0-6 | 建 `tests/factories.py` + `tests/fakes.py`（抽取 `FakeProvider`/`FakeAggregator`） | Q-07 |
| 0-7 | 新增 `.github/workflows/test.yml`，`docker-publish` 加 `needs: pytest` | Q-22 |
| 0-8 | 接入 `ruff`（先只开 `F,E9,B` 规则，`F821` 会立刻抓到 Q-23） | Q-23/Q-26 |

**验收标准**：`pytest` 在干净容器里一次通过；CI 显示 8 passed；覆盖率基线数字被记录。

---

### 3.2 P0 关键路径补测（约 3-4 人日，第 1 迭代）

按「**用户损失 × 缺陷概率 × 补测成本**」排序：

| 优先级 | 目标 | 建议用例数 | 类型 | 关键场景 |
|:---:|---|---:|---|---|
| **P0-1** | **恢复被删的 4 个单测文件** | ~57 | 单元 | 从 `f7bd209^` 恢复；`test_smart_merger.py`（23 例，历史全绿）几乎零成本复活 |
| **P0-2** | `app/routers/auth.py` | 12 | 集成 | 登录成功/密码错误 401/鉴权关闭直通；改密旧密码错误 401、config 写回、改后 session 清空；`check_auth` 三态；**`profile_stats` 真实计数（Q-23 回归）** |
| **P0-3** | `main.py` 鉴权中间件 | 8 | 集成 | 受保护端点匿名 401（参数化 5 个路径）；白名单端点可达（**把 Q-27 的白名单固化为测试**） |
| **P0-4** | `app/routers/wechat.py::dispatch_command` | 14 | 单元 | 帮助/数字选择（有效·越界·无 session·脏 type）/意图前缀解析（参数化 8 组）/空关键词/搜索超时 |
| **P0-5** | `app/routers/wechat.py` 验签 | 6 | 集成 | GET 验签成功→回显；签名错误→**403**；配置缺失→500；POST 解密失败→500；非 text 消息→success |
| **P0-6** | `app/services/download_service.py` | 15 | 单元 | `TokenBucket.acquire/_refill`（令牌耗尽、时间推进用 freezegun）；`_calculate_weight_score` 排序；`_convert_traditional_to_simplified`；`get_audio_url` 各源分支（respx mock）；下载失败重试 |
| **P0-7** | `app/services/favorite_service.py` | 9 | 集成 | 收藏时 cache→favorites 移动；取消时反向；library 目录**不移动**；文件不存在只改状态；移动失败不回滚状态；`song_id` 不存在返回 None（全部 `tmp_path`） |
| **P0-8** | `app/services/notification.py` | 8 | 单元 | `notify_new_song` 载荷结构；`_build_play_url` 各 source；dry-run 抑制；通知器异常不外抛 |
| **P0-9** | `deduplication_service` 缺陷回归 | 12 | 单元 | Q-24 / Q-25 / Q-26 三个缺陷各配 2-4 个断言（修复前 `xfail(strict=True)`，修复后自动转绿） |
| **P0-10** | `app/routers/settings.py` 持久化 | 6 | 集成 | 写入→读取往返一致；非法值拒绝；YAML 与 DB 双写一致性；并发写不丢字段 |

**P0 合计约 147 个用例**，预计把 service 覆盖率带到 ~35%、router 覆盖率带到 ~55%。

---

### 3.3 P1 补测（第 2 迭代，约 3 人日）

| 目标 | 用例数 | 要点 |
|---|---:|---|
| `subscription.py` | 12 | `add_artist` 幂等、`smart_link_sources` 多源关联、`delete_artist` 级联 |
| `scan_service._extract_metadata` / `_analyze_quality` | 15 | 真实小体积样本文件（mp3/flac/m4a 各 1 个放 `tests/assets/`），标签缺失回退、音质判定边界 |
| `scan_service._prune_missing_files` | 6 | 文件消失→记录清理；文件存在→保留；增量模式跳过 pruning |
| `music_providers/aggregator.py` | 14 | `_is_valid_song` 参数化、多源聚合排序、单源失败降级（respx/aioresponses） |
| `music_providers/base.py::async_retry` | 6 | 重试次数、退避间隔（freezegun）、最终失败抛出 |
| `metadata_service` | 12 | 从 `测试/` 迁移 `_preprocess_search_keywords`、`get_best_match_metadata` 渐进式策略顺序 |
| `song_management_service` | 已含在 P0-1 恢复 | — |
| `core/config_manager.py` | 12 | 配置合并优先级、reload、DB/YAML 混合来源（曾有 15 个用例被删，可参考） |
| Alembic 迁移 | 3 | `upgrade head` → `downgrade base` → `upgrade head` 可逆；模型与迁移一致性（`alembic check`） |

---

### 3.4 P2 / 长期（第 3 迭代起）

- **契约测试**：`@pytest.mark.external` 组，每日 cron 跑，验证网易云/QQ音乐/企业微信真实响应结构与录制 fixture 一致（Q-20）。
- **性能回归**：改造为算法复杂度断言（去重 10k 首耗时、扫描 SQL 条数上界），替代 Q-17 的机器相关阈值。
- **前端**：Vue3 部分本次未纳入范围，`web/` 目前同样零测试，建议后续引入 Vitest + Testing Library 覆盖核心组件与 API 层。
- **引入 `pytest-randomly`**：随机化用例顺序，主动暴露 Q-12/Q-13 类顺序依赖（地基修好后再开，否则会一直红）。
- **突变测试**：对 `deduplication_service` / `smart_merger` 这类纯逻辑模块跑一次 `mutmut`，验证断言是否真的有效（这是检测 Q-15 类"假测试"的终极手段）。

---

### 3.5 Mock 策略速查表

| 依赖类型 | 推荐工具 | 用法要点 |
|---|---|---|
| httpx 出站请求 | `respx` | `@respx.mock` 装饰器 + `respx.get(url).mock(httpx.Response(200, json=FX))` |
| aiohttp 出站请求 | `aioresponses` | `with aioresponses() as m: m.get(url, payload=FX)` |
| pyncm / qqmusic-api SDK | `monkeypatch.setattr` | 打在 provider 模块的引用名上，返回 `tests/fixtures/*.json` 录制数据 |
| 数据库 | Q-06 的 `db_session` | 真 SQLite 内存库 + SAVEPOINT，**不要 mock ORM** |
| 文件系统 | `tmp_path` / `tmp_path_factory` | 配合 monkeypatch 改 config 的 `cache_dir`/`favorites_dir`/`library_dir` |
| 时间 | `freezegun` | `last_notified_at` 抑制窗口、`TokenBucket._refill`、会话过期 |
| 企业微信外发 | `MM_NOTIFY_DRY_RUN=1`（autouse） | 默认安全；需验证载荷时再 `monkeypatch` 具体 notifier |
| APScheduler | 不启动调度器 | 只测 `scheduling.py` 的 job 注册参数，不测触发 |
| FastAPI 依赖 | `app.dependency_overrides` | 覆盖 `get_async_session`；测试后 `.clear()` |

**红线**：禁止 `patch` 掉被测对象本身再断言 mock（Q-15）。Code review 判据——**把被测模块删掉，测试必须变红**。

---

## 四、总体测试成熟度评估

### 4.1 成熟度评分

| 维度 | 得分 | 评级 | 依据 |
|---|:---:|---|---|
| 覆盖率 | **1 / 10** | 极差 | 9 个用例 / 15,000 行；service 9%、router 0% |
| 测试有效性 | **2 / 10** | 极差 | 32 个"测试"中 19 个自 mock 自断言、1 个空 body，真正有效仅 12 个 |
| 基础设施可靠性 | **3 / 10** | 差 | conftest fixture 事实失效，被开发者绕开；隔离不成立 |
| 外部依赖隔离 | **3 / 10** | 差 | 无 HTTP mock 层；有真实外发通知风险；仅靠手写 Fake |
| 分层设计 | **2 / 10** | 极差 | 无 unit/integration 分层，无 marker，无 fixture 复用，3 套 DB 搭建并存 |
| CI / 门禁 | **0 / 10** | 无 | PR 不跑测试；测试依赖未声明；无覆盖率门槛 |
| 工程治理 | **1 / 10** | 极差 | 140 个历史测试被批量删除，其中 44 个为红灯用例 |
| **综合** | **12 / 70 ≈ 17%** | **Level 1-（Initial）** | 事实上不存在回归安全网 |

### 4.2 覆盖率总览

| 层 | 模块总数 | 有自动化测试 | 覆盖率 |
|---|---:|---:|---:|
| Services（含 providers） | 27 | 2.5 | **9%** |
| Routers | 14 | 0 | **0%** |
| Repositories | 4 | 0 | **0%** |
| Core | 9 | 0 | **0%** |
| Notifiers | 3 | 0 | **0%** |
| Utils | 2 | 0 | **0%** |
| Models / 迁移 | 8 | 0 | **0%** |
| main.py | 1 | 0 | **0%** |
| **合计** | **68** | **2.5** | **≈ 3.7%（模块）/ ≈ 3%（语句估算）** |

### 4.3 发现分布

| 严重度 | 数量 | 编号 |
|---|---:|---|
| **Critical** | 7 | Q-01, Q-02, Q-03, Q-15, Q-22, Q-23, **Q-29** |
| **High** | 13 | Q-04, Q-05, Q-06, Q-07, Q-08, Q-09, Q-10, Q-16, Q-17, Q-20, Q-24, Q-25, Q-26 |
| **Medium** | 9 | Q-11, Q-12, Q-13, Q-14, Q-18, Q-19, Q-21, Q-27, Q-28 |
| **合计** | **29** | |

> 说明：Q-29（`_get_download_service` 未定义，重新下载/搜索下载 100% 崩溃）于附录 E 补充发现，详见 §6.1。

### 4.4 Top 风险 / 优先级

| 排名 | 风险 | 关联发现 | 影响 | 建议时限 |
|:---:|---|---|---|---|
| **1** | **CI 无门禁 + 测试被批量删除**，质量退化没有任何刹车 | Q-22, Q-02 | 制度性根因，不修则所有补测都会重蹈覆辙 | **立即（本周）** |
| **2** | **`测试/` 的 19 个假测试制造虚假信心**，报告声称"28 用例通过" | Q-15, Q-18 | 决策层误判"已充分测试"，比无测试更危险 | **立即（本周）** |
| **3** | **鉴权 / 微信回调 / 下载 / 收藏零测试**，全是资金·隐私·数据破坏敏感路径 | Q-03, Q-27, Q-28 | 安全与数据完整性事故的直接暴露面 | 第 1 迭代 |
| **4** | **已在主干的 5 个真实缺陷**：**重新下载/搜索下载调用未定义函数直接 500（Q-29，最严重）**、未导入 select、'test' 误判、连字符截断、循环变量泄漏 | **Q-29**, Q-23~Q-26 | Q-29 使两个核心功能完全不可用；其余为用户可感知的功能错误 | **Q-29 立即修**；其余第 1 迭代（含 ruff 接入，一条 `F821` 可拦 Q-23/Q-26/Q-29） |
| **5** | **测试基础设施事实失效**（event_loop / 循环作用域 / rollback 隔离） | Q-04, Q-05, Q-06, Q-07 | 不修则新增测试写不动、写了也会随机红 | 第 0 步（补测前置） |
| **6** | **无外部依赖 mock 层 + 通知可真实外发** | Q-20, Q-21 | provider/下载/元数据 4,000+ 行无法离线测；误发消息风险 | 第 1 迭代 |
| **7** | **全局单例污染 + 并发不安全** | Q-12, Q-13 | 补测规模上去后会爆发"单跑绿全跑红"的幽灵故障 | 第 1-2 迭代 |

### 4.5 一句话给决策层

**当前 music-monitor 的测试体系不仅"覆盖率低"，更严重的是"存在假测试 + 删除红灯用例 + CI 无门禁"这三件事叠加，构成了一个会持续自我恶化的负反馈循环。** 建议把「第 0 步地基（0.5 人日）+ 恢复被删的 57 个历史单测（1 人日）+ CI 门禁（0.5 人日）」作为**下一个迭代的最高优先级卡点任务**——这 2 人日的投入能立刻把有效用例数从 8 提升到约 65，并从制度上止血；随后再按 P0 清单用 3-4 人日覆盖鉴权、下载、收藏、微信、通知五条关键路径。

---

## 5. 附录 D：与架构报告（01）/ 代码质量报告（02）的交叉核对

本节在三份报告全部产出后补写，目的是让交付总监一眼看清**哪些结论被多视角相互印证（可信度最高、必须修）**、**哪些是测试视角独有的增量发现（其他人没看到，容易漏掉）**。

### D.1 相互印证（≥2 份报告独立命中，优先级自动上浮）

| 主题 | 测试报告 | 代码质量报告 | 架构报告 | 交叉结论 |
|---|---|---|---|---|
| 鉴权中间件白名单放行 `/api/audio/`、`/api/test_notify_card` | **Q-27**（视角：这段分支零测试，改坏了没人知道） | **C-02 Critical**（视角：未授权访问 + 通知轰炸） | **A-2x**（视角：白名单机制本身"忘记加白/误加白"不可预期） | **三方独立命中 → 定为全项目第一优先级安全缺陷**。修复后必须同时补 Q-27 的中间件参数化测试，否则下次重构会再放开 |
| 大面积吞异常导致故障不可观测 | **Q-23**（吞异常把 `NameError` 变成"静默返回 0"，是缺陷能存活多版本的直接原因） | **C-03 High**（列出 25+ 处裸 `except`） | A-0x（可测试性/边界） | **C-03 是"病"，Q-23 是"病症实例"**。建议以 Q-23 作为 C-03 整改的验收样例：修完导入后，该接口应能在测试中断言真实计数 |
| 通知配置读取源不一致 / 通知可真实外发 | **Q-21**（无 dry-run，跑测试会真发企业微信消息） | C-01/C-05（密钥明文、配置三源分裂） | **A-02 High**（UI 改配置但 `test_notify` 读旧值） | 三方都指向 notify 链路。**补测顺序应排在配置收敛之后**，否则测试要同时适配两套配置源 |
| 全局单例 / 配置全局字典 | **Q-12**（单例跨用例污染，规模化补测后会爆发幽灵故障） | C-05（三套配置真相） | A-01（双配置源为全篇根因矛盾） | 架构侧收敛配置是**测试可规模化的前置条件**，两件事必须排在同一迭代 |

### D.2 测试视角独有的增量发现（另外两份报告均未命中）

已用 grep 全量核对 `.review/01-architecture.md` 与 `.review/02-code-quality.md`，以下 4 条**仅在本报告中出现**——它们是通过"给去重逻辑写用例 + 离线复现输入输出"才暴露的，纯静态阅读容易跳过：

| 编号 | 缺陷 | 为什么只有测试视角能发现 | 建议动作 |
|---|---|---|---|
| **Q-23** | `auth.py:216/221` 使用未导入的 `select` | 静态阅读只会看到 `except Exception` 的"防御性写法"，不会意识到**整个 try 块从未成功执行过**；只有构造请求断言返回值才暴露 | 修 1 行导入 + 补 1 条断言真实计数的用例 |
| **Q-24** | `inst_markers` 含调试残留 `'test'` 且为子串匹配 | 需要代入真实标题数据（如 `Greatest Hits`）才能看出误判；读代码只觉得是普通关键词表 | 删除 `'test'`，改词边界匹配 + 参数化用例 |
| **Q-25** | `re.sub(r'[\|｜－-].*$','')` 过度截断标题 | 需要跑一遍输入输出才发现"所有 `a` 开头的标题被砍成 `a` 并互相合并" | 收紧正则 + 补数据破坏级回归用例 |
| **Q-26** | 循环变量 `item` / `item_sources` 泄漏到循环外使用 | 属于 pylint `undefined-loop-variable` 类问题，人眼极易滑过 | 接入 ruff（`F821` + `PLW2901`）即可长期防回归 |

> **给决策层的含义**：这 4 条缺陷已在主干存活多个版本且用户可感知，而两轮人工代码审查都没发现——这正是"必须有自动化测试 + 静态门禁"最有力的实证。它们不是"补测试能顺便发现的额外收获"，而是**当前审查方式的能力上限证明**。

### D.3 三份报告的修复排序建议（合并视图）

1. **本周**：C-02/Q-27 鉴权白名单收口 → Q-22 CI 门禁上线（无门禁则后面所有修复都会回退）→ 清理 Q-15 的 19 个假测试（避免误导验收）
2. **第 1 迭代**：Q-23~Q-26 四个真实缺陷 + ruff 接入 → 第 0 步测试地基（0.5 人日）→ 恢复被删的 57 个历史单测
3. **第 1-2 迭代**：A-01/C-05 配置收敛（测试规模化前置）→ P0 五条关键路径补测（鉴权/下载/收藏/微信/通知，3-4 人日）
4. **第 2 迭代+**：C-03 吞异常整改（以 Q-23 为验收样例）、C-04 超时统一（配套 respx 超时用例）

---

## 6. 附录 E：Q-29 新增缺陷 + Q-12 单例依赖注入改造清单

> 本节应架构师（software-architect）请求补写。在梳理单例调用点时，扫出了**第 5 个主干真实缺陷 Q-29**，严重度 Critical，故一并记录。

### E.1 Q-29 ｜Critical｜`_get_download_service()` 全项目无定义，「重新下载」与「搜索下载」两个功能 100% 崩溃

**位置**：`app/services/song_management_service.py:161`、`app/services/song_management_service.py:308`

**证据链（全部可复核）**：

1. 全仓库检索 `_get_download_service`（带前导下划线）**仅命中 2 处，且均为调用，零定义**：
   ```
   app/services/song_management_service.py:161:  download_service = _get_download_service()
   app/services/song_management_service.py:308:  download_service = _get_download_service()
   ```
2. 该文件 `:32` 导入的是**无下划线**的版本：
   ```python
   from app.services._singletons import get_download_service, get_aggregator, get_metadata_service
   ```
   即正确名字是 `get_download_service`，调用处多写了一个下划线。
3. 该名字既非局部变量、也非模块全局、更非内置 → 运行到该行必然 `NameError: name '_get_download_service' is not defined`。

**与 Q-23 的关键差异（决定修复优先级）**：
Q-23 被 `except Exception` 吞成「静默返回 0」，用户只觉得数字不准；而 Q-29 所在的两个方法装饰器为

| 方法 | 行号 | 装饰器 | `raise_on_critical` | 运行时表现 |
|---|---|---|---|---|
| `redownload_song` | `:118`（装饰器 `:117`） | `@handle_service_errors(fallback_value=False)` | **True（默认）** | NameError 被记 `critical` 日志后**重新抛出** → 接口 500 |
| `download_song_from_search` | `:240`（装饰器 `:239`） | `@handle_service_errors(fallback_value={"success": False, ...})` | **True（默认）** | 同上 → 接口 500 |

`app/utils/error_handler.py:92-97` 的兜底分支为 `except Exception → _log("critical") → if raise_on_critical: raise`，而 `raise_on_critical` 默认值是 `True`（`error_handler.py:29`），两处均未显式传 `False`，因此**异常会上抛，不是静默降级**。

**影响面**：调用链完整可达，非死代码——
```
POST /api/library/.../redownload   (app/routers/library.py:274 → :283)
        → LibraryService.redownload_song            (app/services/library.py:92 → :107)
        → SongManagementService.redownload_song     (song_management_service.py:118 → :161 💥)

POST /api/library/... 搜索下载       (app/routers/library.py:333)
        → LibraryService.download_song_from_search  (app/services/library.py:111 → :127)
        → SongManagementService.download_song_from_search (:240 → :308 💥)
```
即「重新下载歌曲」和「从搜索结果下载」这两个核心用户功能**在当前主干上必定 500**，无任何降级路径。

**修复（1 行 × 2 处）**：
```python
# song_management_service.py:161 与 :308
- download_service = _get_download_service()
+ download_service = get_download_service()
```

**回归用例（必须同时补，否则会再犯）**：
```python
async def test_redownload_song_resolves_download_service(monkeypatch, db_session):
    """Q-29 回归：确保不再出现未定义的 _get_download_service"""
    svc = SongManagementService()
    fake = FakeDownloadService(audio_url="http://x/a.flac")
    monkeypatch.setattr(sms_mod, "get_download_service", lambda: fake)
    ok = await svc.redownload_song(db_session, song_id=1, source="netease", source_id="1")
    assert ok is not False          # 不再 NameError/500
    assert fake.get_audio_url_called
```

**根因与长效防护**：与 Q-26 完全同类（`ruff` 的 `F821 undefined-name` 一条规则即可在 CI 拦截 Q-23 / Q-26 / Q-29 三条）。这再次证明**静态门禁的投入产出比高于补测试**——3 条 Critical/High 缺陷，一条 lint 规则全覆盖。

> **给 software-engineer 的优先级建议**：Q-29 应排在 Q-23 之前修复，因为它是「功能完全不可用（500）」而非「数据不准」。

---

### E.2 Q-12 单例改依赖注入 — 完整改造清单

#### E.2.1 单例全景（共 6 个，比原 Q-12 描述的多 3 个）

| # | 单例 | 定义位置 | 形态 | 可测试性 |
|:-:|---|---|---|:-:|
| 1 | `get_download_service()` | `_singletons.py:22-29` | 惰性 `global` | ❌ 缓存后无法替换 |
| 2 | `get_metadata_service()` | `_singletons.py:32-39` | 惰性 `global` | ❌ |
| 3 | `get_aggregator()` | `_singletons.py:42-49` | 惰性 `global` | ❌ |
| 4 | `get_new_release_monitor()` | `new_release_monitor.py:199-206` | 惰性 `global _service` | ❌ |
| 5 | `get_auto_download_service()` | `auto_download_service.py:102-105` | 惰性 `global _service` | ❌ |
| 6 | `task_monitor` | `task_monitor.py:181` | **饿汉式模块级实例** | ❌❌ **最差**：import 即创建，连 monkeypatch 时机都难把握 |

`task_monitor` 被 `routers/task_control.py`(4次)、`services/metadata_healer.py`(8次)、`services/scan_service.py`(10次) 直接引用，共 22 处，是耦合最重的一个。

#### E.2.2 需要改造的调用点（共 30 处，按改造方式分三类）

**A 类 — 路由层：改 `Depends` 注入（11 处，收益最高，改完即可用 `dependency_overrides`）**

| 文件:行 | 所在端点 | 当前写法 | 目标 |
|---|---|---|---|
| `discovery.py:49` | `search_discovery` (`GET /search`) | `aggregator = get_aggregator()` | `agg: MusicAggregator = Depends(get_aggregator)` |
| `discovery.py:69` | `search_download` (`GET /search_download`) | `service = get_download_service()` | `svc: DownloadService = Depends(get_download_service)` |
| `discovery.py:128` | `probe_qualities_endpoint` | `service = get_download_service()` | 同上 |
| `discovery.py:173` | `search_artists` | `aggregator = get_aggregator()` | 同上 |
| `discovery.py:192` | `get_artist_online_songs` | `aggregator = get_aggregator()` | 同上 |
| `metadata.py:47` | `get_lyrics` (`GET /lyrics`) | `metadata_service = get_metadata_service()` | `md: MetadataService = Depends(get_metadata_service)` |
| `metadata.py:66` | `get_cover` (`GET /cover`) | 同上 | 同上 |
| `metadata.py:92` | `fetch_all_metadata` (`POST /fetch-all`) | 同上 | 同上 |
| `media.py:106-108` | 播放相关端点 | 函数内 `import` + 调用 | 提到模块顶层 + `Depends` |
| `wechat.py:221` | 微信指令分支 | `aggregator = get_aggregator()` | `Depends`（见下方注意） |
| `wechat.py:256` / `:296` | 微信指令分支 / 下载 | `get_aggregator()` / `get_download_service()` | 同上 |

> **wechat.py 注意**：这 3 处在 `dispatch_command` 的内部分支里（非端点签名层），无法直接 `Depends`。建议**把 `dispatch_command` 改成接收 service 参数**，由端点函数 `Depends` 注入后透传——这同时能解掉我原报告 Q-28 的「session 泄漏」问题，两条一起改。

**B 类 — 服务层 `__init__` 内取单例：改构造函数参数默认值（7 处）**

| 文件:行 | 类 | 当前 | 目标 |
|---|---|---|---|
| `new_release_monitor.py:35` | `NewReleaseMonitorService` | `self.aggregator = get_aggregator()` | `def __init__(self, aggregator=None): self.aggregator = aggregator or get_aggregator()` |
| `song_management_service.py:44-45` | `SongManagementService` | `get_aggregator()` / `get_metadata_service()` | 同上（双参数） |
| `subscription.py:128` | `SubscriptionService` | `aggregator = get_aggregator()` | 同上 |
| `library.py:45-49` | `LibraryService` | 函数内 import + `get_aggregator()` | 同上 |
| `artist_refresh_service.py:41-42` | `ArtistRefreshService` | 函数内 import + `get_aggregator()` | 同上 |
| `metadata_healer.py:39-40` | `MetadataHealer` | 函数内 import + `get_metadata_service()` | 同上 |
| `wechat_download_service.py:47-56` | `WechatDownloadService` | 函数内 import + `get_download_service()` | 同上 |

> 这是**成本最低、破坏性最小**的一档：`x or get_default()` 模式对生产零行为变更，测试里直接 `Service(aggregator=FakeAggregator())`。**建议第一步只做 B 类**，7 处改完，服务层单测立刻可写——不必等 A 类的路由重构。

**C 类 — 模块级函数内取单例：改显式传参（2 处）**

| 文件:行 | 函数 | 说明 |
|---|---|---|
| `media_service.py:198-205` | 内部方法 | 同时取 download + metadata 两个单例 |
| `media_service.py:374-376` | 模块级函数 | 取 aggregator |

#### E.2.3 conftest 如何切 `dependency_overrides`（可直接粘贴）

```python
# tests/conftest.py 追加

@pytest.fixture
def fake_aggregator():
    """离线聚合器：不发任何真实网络请求"""
    class _FakeAggregator:
        def __init__(self):
            self.calls = []
            self.songs_by_source = {}
        async def search(self, keyword, **kw):
            self.calls.append(("search", keyword))
            return self.songs_by_source.get("default", [])
        async def get_artist_songs(self, source, artist_id, **kw):
            return self.songs_by_source.get(source, [])
    return _FakeAggregator()


@pytest.fixture
def fake_download_service():
    class _FakeDownloadService:
        def __init__(self):
            self.get_audio_url_called = False
        async def get_audio_url(self, source, source_id, quality=None):
            self.get_audio_url_called = True
            return {"url": "http://test.local/a.flac", "quality": quality or 999}
        async def find_best_match(self, title, artist):
            return None
        async def probe_available_qualities(self, *a, **kw):
            return [999]
    return _FakeDownloadService()


@pytest.fixture
async def api_client(test_engine, db_session, fake_aggregator, fake_download_service):
    """
    完整隔离的 API 客户端：DB 走内存 SAVEPOINT，外部服务全部替身。
    A 类改造完成后，下面 3 行 override 即可生效。
    """
    from main import app
    from core.database import get_async_session
    from app.services._singletons import (
        get_aggregator, get_download_service, get_metadata_service,
    )

    app.dependency_overrides[get_async_session] = lambda: db_session
    app.dependency_overrides[get_aggregator] = lambda: fake_aggregator
    app.dependency_overrides[get_download_service] = lambda: fake_download_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()      # 关键：防止跨用例泄漏
```

**过渡期（A 类尚未改完时）的兜底**——用 autouse fixture 强制清空单例缓存，避免用例间互相污染：

```python
@pytest.fixture(autouse=True)
def _reset_singletons():
    """Q-12 过渡方案：每个用例前后清空所有全局单例"""
    import app.services._singletons as s
    import app.services.new_release_monitor as nr
    import app.services.auto_download_service as ad

    for mod, names in (
        (s,  ("_download_service", "_metadata_service", "_aggregator")),
        (nr, ("_service",)),
        (ad, ("_service",)),
    ):
        for n in names:
            setattr(mod, n, None)
    yield
    for mod, names in (
        (s,  ("_download_service", "_metadata_service", "_aggregator")),
        (nr, ("_service",)),
        (ad, ("_service",)),
    ):
        for n in names:
            setattr(mod, n, None)
```

> `task_monitor`（饿汉式）无法用上面的方式复位，**必须先改成惰性 `get_task_monitor()`**，否则它会是唯一残留的污染源。这条建议由架构侧拍板是否纳入本次范围。

#### E.2.4 建议的落地顺序与工作量

| 步骤 | 内容 | 工作量 | 风险 | 立即收益 |
|:-:|---|:-:|:-:|---|
| 1 | **B 类 7 处**改 `__init__(self, dep=None)` | 0.5 人日 | 极低（生产零变更） | 服务层单测可写 |
| 2 | 加 `_reset_singletons` autouse fixture | 0.1 人日 | 无 | 消除用例间污染 |
| 3 | **A 类 8 处**（discovery/metadata/media）改 `Depends` | 0.5 人日 | 低 | 路由层可 override |
| 4 | `task_monitor` 饿汉 → 惰性 `get_task_monitor()` | 0.3 人日 | 中（22 处引用） | 最后一个污染源清除 |
| 5 | **A 类 wechat 3 处** + `dispatch_command` 传参（并修 Q-28 session 泄漏） | 0.5 人日 | 中 | 微信链路可测 |
| | **合计** | **约 1.9 人日** | | |

**我的建议**：步骤 1+2 应当**无条件先做**（0.6 人日，零风险），它解锁了 P0 清单里绝大部分服务层用例；步骤 3-5 可以和架构侧的会话入口统一（A-13）合并成一次重构，避免同一批文件改两遍。

---

### E.3 Q-23「dev 强制重抛」的环境变量命名建议

架构师询问统一命名。综合考量后建议：

**变量名：`MM_STRICT_ERRORS`**（`MM` = music-monitor 项目前缀）

| 取值 | 语义 | 适用环境 |
|---|---|---|
| `1` / `true` | 所有被装饰器捕获的**未预期异常**一律重抛，不降级 | 本地开发、CI、测试 |
| `0` / 未设置 | 维持现有降级行为（向后兼容，生产默认） | 生产 |

**理由**：
1. 用**项目前缀 `MM_`** 而非裸 `STRICT_ERRORS`，避免与容器里其他组件的环境变量撞名（该项目已有 `PUID`/`PGID` 这类无前缀变量，容易冲突，不宜再增加）。
2. 用 `STRICT_ERRORS` 而非 `DEBUG`/`ENV=dev`：语义单一、正交。`DEBUG` 往往被 FastAPI/日志/前端多方复用，语义会被稀释；而这里要表达的就是「异常是否严格」这一件事。
3. **不要**命名为 `RAISE_ON_CRITICAL`——它和 `handle_service_errors` 的入参同名，会让读者误以为是「覆盖单个装饰器入参」，实际语义是「全局提升严格度」。

**建议实现（`error_handler.py` 顶部，约 25 行处）**：
```python
import os

_STRICT = os.getenv("MM_STRICT_ERRORS", "").lower() in ("1", "true", "yes")

def handle_service_errors(fallback_value=None, raise_on_critical=True, log_level="error"):
    ...
            except Exception as e:
                _log("critical", f"未预期的错误: {str(e)}", exc_info=e)
                if raise_on_critical or _STRICT:   # ← 严格模式下无条件重抛
                    raise
                return fallback_value
```

同时在 CI 的 test job 里固定注入：
```yaml
env:
  MM_STRICT_ERRORS: "1"
```

**这样做的直接效果**：Q-23（`select` 未导入）这类被 `except Exception` 吞掉的 `NameError`，在 CI 里会**直接把用例打红**，而不是让测试通过后到生产才发现返回 0。换句话说，`MM_STRICT_ERRORS=1` 是把「吞异常」（C-03）从一个**架构缺陷**转化为一个**可被 CI 捕获的信号**——这是 C-03 整改中性价比最高的一步，比逐个改 25 处 `except` 快得多，且不影响生产行为。

> **注意**：该开关只影响装饰器 `handle_service_errors` / `ErrorContext` 这类**统一入口**。散落在各处的裸 `except:`（C-03 列出的 25+ 处）不受它管辖，仍需逐个整改——但可以放到后续迭代。

---

*本报告基于只读静态审查、git 历史取证、`.pytest_cache` 执行快照取证与逻辑离线复现完成，审查过程中未修改任何源码、测试或配置文件。所有位置引用均已核对到具体 file:line。附录 D 于三份报告齐备后补写；附录 E 应架构师请求补写，其中 Q-29 为新增 Critical 缺陷，发现总数由 28 条更新为 29 条（Critical 7 / High 13 / Medium 9）。*
