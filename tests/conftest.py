# -*- coding: utf-8 -*-
"""
pytest 全局测试夹具 (Test Fixtures)

设计目标
========
1. **真隔离**：被测代码内部大量自行调用 `await session.commit()`。旧版 conftest 在
   teardown 里 `rollback()` 是无效的——commit 已经把数据落库，rollback 无事可回滚，
   数据于是泄漏给后续测试，造成"单跑绿、全量跑红"的经典幽灵失败。
   本文件采用 SQLAlchemy 2.0 的 **SAVEPOINT 方案**：
       外层连接开启一个真实事务  ->  Session 以 join_transaction_mode="create_savepoint"
       加入该事务  ->  被测代码的每次 commit() 实际只是 RELEASE SAVEPOINT
       ->  teardown 时回滚外层事务，组内所有写入一次性蒸发。

2. **无废弃 API**：移除了自定义 `event_loop` fixture（pytest-asyncio >= 0.23 已废弃，
   0.26+ 会直接报错）。事件循环完全交给 `pytest.ini` 里的 `asyncio_mode = auto` 管理。

3. **全局状态复位**：项目里存在若干进程级单例/全局可变字典
   （`core.config.config`、`core.config_manager._config_manager`、
   `DeduplicationService._normalize_title` 的 lru_cache）。
   autouse 夹具 `_isolate_global_state` 在每个测试前后做快照/还原，防止串扰。

Author: music-monitor QA
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# sys.path 引导
# ---------------------------------------------------------------------------
# 无论用 `pytest` / `python -m pytest` / IDE 哪种方式启动，都保证项目根目录可被
# import（否则 `from app.services... import ...` 会 ModuleNotFoundError）。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import (  # noqa: E402  (必须在 sys.path 引导之后)
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models.base import Base  # noqa: E402

# 显式导入 models 包，触发所有 ORM 类注册到 Base.metadata。
# 否则 create_all() 只会建出"恰好被某个测试文件 import 过"的表，
# 表的存在与否取决于收集顺序 —— 又一个幽灵失败来源。
import app.models  # noqa: E402,F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ===========================================================================
# 数据库夹具
# ===========================================================================
@pytest_asyncio.fixture
async def test_engine():
    """
    每个测试独立的内存库引擎。

    为什么是 function 作用域而不是 session 作用域？
    ------------------------------------------------
    pytest-asyncio >= 0.23 默认给每个测试分配 function 级事件循环。若引擎是
    session 级，它会绑定在创建它的那个循环上，后续测试用另一个循环访问 aiosqlite
    连接会抛 `Future attached to a different loop`。跨版本兼容性最好、也最不容易
    出玄学问题的做法就是 function 级引擎——SQLite 内存库 + create_all 只需几毫秒，
    这点开销完全可以接受。

    StaticPool + check_same_thread=False：`:memory:` 库的生命周期绑定在单个连接上，
    StaticPool 保证整个引擎始终复用同一条连接，否则每次 checkout 都会拿到一个全新的
    空库。
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    提供一个"写了也白写"的 AsyncSession —— 测试结束后所有变更全部回滚。

    关键点：Session 必须绑定到一个 **已经开启事务的 Connection**，
    `join_transaction_mode="create_savepoint"` 才会生效。
    如果直接把 engine 传给 sessionmaker，Session 会自己去 checkout 连接、
    自己开事务，该参数形同虚设，隔离也就无从谈起。
    """
    async with test_engine.connect() as conn:
        # 外层事务：被测代码的 commit() 都会退化成 RELEASE SAVEPOINT，
        # 无法真正提交到库里。
        outer_trans = await conn.begin()

        session_factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

        # 一次性抹掉本测试的所有写入
        if outer_trans.is_active:
            await outer_trans.rollback()


# ===========================================================================
# 全局状态隔离
# ===========================================================================
@pytest.fixture(autouse=True)
def _isolate_global_state():
    """
    快照/还原进程级全局可变状态，避免测试之间互相污染（审查报告 Q-12 单例问题）。

    覆盖三处：
      1. `core.config.config`      —— legacy 全局 dict，很多模块 `from core.config import config`
                                      直接持有引用，因此必须**原地** clear+update，不能重新赋值。
      2. `core.config_manager._config_manager` —— ConfigManager 单例。
                                      注意：只在单例**已经存在**时才快照，绝不主动
                                      调用 get_config_manager() 去把它创建出来
                                      （构造函数会读盘 + 读环境变量，有副作用）。
      3. `DeduplicationService._normalize_title.cache_clear()` —— lru_cache 是隐式全局态。
    """
    # ---- 快照 ----
    core_config_mod = None
    config_snapshot = None
    try:
        import core.config as core_config_mod  # type: ignore[no-redef]

        config_snapshot = copy.deepcopy(getattr(core_config_mod, "config", None))
    except Exception:  # pragma: no cover - 导入失败时降级为不隔离
        core_config_mod = None

    cm_mod = None
    manager_before = None
    manager_config_snapshot = None
    try:
        import core.config_manager as cm_mod  # type: ignore[no-redef]

        manager_before = getattr(cm_mod, "_config_manager", None)
        if manager_before is not None:
            manager_config_snapshot = copy.deepcopy(
                getattr(manager_before, "_config", None)
            )
    except Exception:  # pragma: no cover
        cm_mod = None

    _clear_dedup_cache()

    yield

    # ---- 还原 ----
    if core_config_mod is not None and isinstance(config_snapshot, dict):
        live = getattr(core_config_mod, "config", None)
        if isinstance(live, dict):
            live.clear()
            live.update(config_snapshot)

    if cm_mod is not None:
        if manager_before is not None:
            cm_mod._config_manager = manager_before
            if manager_config_snapshot is not None:
                manager_before._config = manager_config_snapshot
        else:
            # 单例是在本测试期间被创建的 -> 丢弃，别留给下一个测试
            cm_mod._config_manager = None

    _clear_dedup_cache()


def _clear_dedup_cache() -> None:
    """清空 DeduplicationService._normalize_title 的 lru_cache（若可用）。"""
    try:
        from app.services.deduplication_service import DeduplicationService

        cache_clear = getattr(
            DeduplicationService._normalize_title, "cache_clear", None
        )
        if callable(cache_clear):
            cache_clear()
    except Exception:  # pragma: no cover
        pass


# ===========================================================================
# API / HTTP 夹具
# ===========================================================================
@pytest_asyncio.fixture
async def app_instance():
    """
    延迟导入 FastAPI app。

    `main` 的导入链很重（scheduler / providers / websocket ...），放在模块顶层
    import 会拖慢所有纯逻辑单测，甚至在缺依赖的环境里直接让收集失败。
    因此这里按需导入，导入失败则 skip 而不是 error。
    """
    try:
        from main import app  # noqa: WPS433
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"无法导入 FastAPI app，跳过 API 测试: {exc}")
    return app


@pytest_asyncio.fixture
async def api_client(app_instance, db_session):
    """
    零改造接入的 API 测试客户端。

    用法::

        async def test_health(api_client):
            resp = await api_client.get("/api/system/health")
            assert resp.status_code == 200

    实现要点：
      * `core.database.get_async_session` 是全项目唯一的 DB 依赖注入点
        （所有 router 都是 `Depends(get_async_session)`），因此只需 override 这一个
        依赖，整个应用就会跑在测试事务里。
      * 用 `ASGITransport` 直连 ASGI app，不起真实端口、**不触发 lifespan**，
        因而不会执行 `async_init_db()` 去动真实的 config/music_monitor.db。
      * 若被测接口带鉴权，请在测试内自行注入 header 或 override 对应的鉴权依赖。
    """
    from httpx import ASGITransport, AsyncClient

    from core.database import get_async_session

    async def _override_get_async_session():
        yield db_session

    app_instance.dependency_overrides[get_async_session] = _override_get_async_session
    transport = ASGITransport(app=app_instance)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app_instance.dependency_overrides.pop(get_async_session, None)
