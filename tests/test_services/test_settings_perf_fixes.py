# -*- coding: utf-8 -*-
"""
settings 性能专项回归 (settings GET 同步阻塞 + 同步引擎不 dispose)

修复内容:
1. GET /api/settings 不再强制 reload —— 消除每次 GET 的同步 DB 读 +
   config.yaml 重写副作用 (async 事件循环内同步阻塞);
2. ConfigManager 同步引擎懒创建复用 —— 旧实现每次 reload 都 create_engine
   且从不 dispose, SQLite 连接/文件句柄持续泄漏;
3. PATCH 的 reload_config() 移入线程池 (asyncio.to_thread) —— 避免阻塞事件循环。
"""
from __future__ import annotations

import pytest_asyncio


# --- 1. GET 不再触发 reload ------------------------------------------------
async def test_get_settings_does_not_trigger_reload(monkeypatch):
    """GET /api/settings 不应再强制 reload (同步 DB 读 + 写 config.yaml 副作用)。"""
    import core.config_manager as cm_mod
    from app.api.v1 import settings as settings_api

    reload_called = []

    # 模拟 reload 抛异常: 若 GET 路径仍调用 reload, 测试将直接失败
    def _explode(*a, **k):
        reload_called.append(1)
        raise AssertionError("get_settings 不应触发 reload (同步阻塞 + 写盘副作用)")

    monkeypatch.setattr(cm_mod.ConfigManager, "reload", _explode)

    result = await settings_api.get_settings()

    assert reload_called == []
    assert isinstance(result, dict)
    assert "download" in result  # 内存配置已含业务默认值


# --- 2. 同步引擎懒创建 + 复用 ----------------------------------------------
def test_config_manager_reuses_sync_engine(monkeypatch):
    """多次 reload 只 create_engine 一次, 不再每次新建+泄漏。"""
    import core.config_manager as cm_mod
    from core.config_manager import ConfigManager

    # 隔离: 同步引擎指向内存库, 避免读写真实 config/music_monitor.db
    monkeypatch.setattr("core.database.DATABASE_URL", "sqlite:///:memory:")
    # 隔离: 不重写真实 config.yaml
    monkeypatch.setattr(cm_mod.ConfigManager, "_normalize_yaml_file", lambda self: None)

    real_create_engine = cm_mod.create_engine
    created = []

    def _spy(*a, **k):
        created.append((a, k))
        return real_create_engine(*a, **k)

    monkeypatch.setattr(cm_mod, "create_engine", _spy)

    manager = ConfigManager(config_file="config/config.yaml")
    assert manager._sync_engine is None  # 懒创建: 未 reload 前不建引擎

    manager.reload()
    manager.reload()
    manager.reload()

    assert len(created) == 1, f"create_engine 应只调用一次, got {len(created)}"
    assert manager._sync_engine is not None
    # 复用同一个引擎实例
    engine = manager._sync_engine
    manager.reload()
    assert manager._sync_engine is engine


# --- 3. PATCH 后内存配置更新 (reload 生效) ---------------------------------
@pytest_asyncio.fixture
async def settings_client(test_engine):
    """复用 smoke 模式: auth 关闭 + DB 重定向内存库。"""
    import httpx
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from core.database import get_async_session

    from main import app

    factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override_session

    from core.config_manager import get_config_manager

    get_config_manager()._config.setdefault("auth", {})["enabled"] = False

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://smoke") as client:
        yield client

    app.dependency_overrides.pop(get_async_session, None)


async def test_update_settings_patch_applies_and_reloads(
    settings_client, test_engine, monkeypatch
):
    """PATCH 写库成功 + 触发配置重载 (to_thread 不阻塞事件循环) + 响应脱敏。"""
    import core.database
    import core.config_manager as cm_mod
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.api.v1 import settings as settings_api
    from app.models.settings import SystemSettings

    # 隔离: reload 的同步 DB 读指向内存库 + 不重写真实 config.yaml
    monkeypatch.setattr(core.database, "DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setattr(cm_mod.ConfigManager, "_normalize_yaml_file", lambda self: None)

    # spy: 验证 PATCH 触发了 reload (走 asyncio.to_thread, 事件循环不被同步 DB 读阻塞)
    reload_called = []
    monkeypatch.setattr(
        settings_api, "reload_config", lambda: reload_called.append(1)
    )

    resp = await settings_client.patch(
        "/api/settings",
        json={"download": {"max_concurrent_downloads": 5}},
    )
    assert resp.status_code == 200, resp.text

    # 1. reload 被触发一次
    assert reload_called == [1]

    # 2. PATCH 真正写库成功 (settings_client 的 DB 是 test_engine, commit 已落库)
    async with AsyncSession(test_engine) as s:
        row = (
            await s.execute(select(SystemSettings).filter_by(id=1))
        ).scalars().first()
    assert row is not None
    assert row.download_settings.get("max_concurrent_downloads") == 5

    # 3. 响应脱敏 (回显不含明文凭据)
    body = resp.json()
    assert body["auth"]["password"] == "***redacted***"
