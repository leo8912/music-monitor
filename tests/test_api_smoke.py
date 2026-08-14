# -*- coding: utf-8 -*-
"""
API 冒烟测试 —— 阶段 0 安全网

目的不是覆盖业务逻辑，而是**固化当前真实行为**，为一次性重建提供回归基准：

1. `test_smoke_get_ok`：这些端点现在能通，重建后必须还能通。
2. `test_known_broken_*`（xfail strict）：已确认的真实缺陷。它们现在必然失败；
   等重建把问题修掉后，xfail 会变成 XPASS 而**导致测试失败**，从而强制删除标记。
   这样缺陷清单不会腐烂成一份没人看的文档。

约束
====
- 不启用 lifespan：`main.lifespan` 会 `scheduler.start()` 并推送企微上线通知。
- 不触碰任何走外网的端点（歌词、企微自检、通知发送），避免测试依赖第三方与真发消息。
"""
from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.database import get_async_session


@pytest_asyncio.fixture
async def smoke_client(test_engine):
    """未走 lifespan 的 ASGI 客户端，DB 依赖被重定向到内存库，鉴权关闭。"""
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


SMOKE_GET_OK = [
    "/api/version",
    "/api/check_auth",
    "/api/user",
    "/api/status",
    "/api/settings",
    "/api/profile_stats",
    "/api/library/songs",
    "/api/library/local-songs",
    "/api/subscription/artists",
    "/api/history",
    "/api/download-history/",
    "/api/download-history/stats",
]


@pytest.mark.parametrize("path", SMOKE_GET_OK)
async def test_smoke_get_ok(smoke_client, path):
    resp = await smoke_client.get(path)
    assert resp.status_code == 200, resp.text


async def test_settings_response_is_sanitized(smoke_client):
    """[Fix C-01] 回归锁：/api/settings 里的凭据字段必须是脱敏占位值。"""
    payload = (await smoke_client.get("/api/settings")).json()
    creds = {
        payload.get("auth", {}).get("secret_key"),
        payload.get("auth", {}).get("password"),
    }
    assert creds == {"***redacted***"}


async def test_check_notify_status_keeps_connected_field(smoke_client):
    """[4.5] 回归锁：response_model 过滤不得吞掉 check_notify_status 的 connected 字段。

    前端 NotifySettings.vue / SettingsModal.vue 依赖 result.connected 判断通道连通性。
    """
    resp = await smoke_client.get("/api/check_notify_status/wecom")
    assert resp.status_code == 200
    payload = resp.json()
    assert "connected" in payload, f"connected 字段被 response_model 过滤: {payload}"
    assert payload["connected"] in (True, False)


async def test_scan_library_keeps_result_fields(smoke_client):
    """[4.5] 回归锁：library /scan 的 new_files_found/removed_files_count 不得被过滤。

    前端 library.ts scanLibrary 依赖这两个字段展示扫描结果。
    """
    resp = await smoke_client.post("/api/library/scan")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "new_files_found" in payload, f"new_files_found 被过滤: {payload}"
    assert "removed_files_count" in payload, f"removed_files_count 被过滤: {payload}"


async def test_login_rejects_bad_credentials(smoke_client):
    """鉴权开启时错误口令必须被拒。"""
    from core.config_manager import get_config_manager

    get_config_manager()._config.setdefault("auth", {})["enabled"] = True
    resp = await smoke_client.post(
        "/api/login", json={"username": "nobody", "password": "wrong"}
    )
    assert resp.status_code == 401


async def test_wecom_callback_requires_signature(smoke_client):
    """[D8] 微信回调是对外契约，缺签名参数必须 422 而不是 500。"""
    resp = await smoke_client.get("/api/wecom/callback")
    assert resp.status_code == 422


async def test_auth_enforced_via_router_dependencies(smoke_client):
    """[4.4] 鉴权改为路由级依赖后，开启鉴权时受保护端点必须 401。

    - 受保护端点（/api/status、/api/settings、/api/library/songs）→ 401
    - 匿名端点（/api/check_auth、/api/test_ws、/api/wecom/callback）→ 非 401
    """
    from core.config_manager import get_config_manager

    cm = get_config_manager()
    cm._config.setdefault("auth", {})["enabled"] = True
    try:
        for path in ("/api/status", "/api/settings", "/api/library/songs"):
            resp = await smoke_client.get(path)
            assert resp.status_code == 401, f"{path} 应返回 401, got {resp.status_code}"

        for path in ("/api/check_auth", "/api/test_ws", "/api/wecom/callback"):
            resp = await smoke_client.get(path)
            assert resp.status_code != 401, f"{path} 是匿名端点, 不应 401"
    finally:
        cm._config.setdefault("auth", {})["enabled"] = False


# ===========================================================================
# 已确认缺陷（重建后应逐条修复并删除对应 xfail）
# ===========================================================================
@pytest.mark.xfail(
    strict=True, reason="R9: system.py 调用了 APILogHandler 上不存在的 get_recent_logs"
)
async def test_known_broken_logs_endpoint(smoke_client):
    assert (await smoke_client.get("/api/logs")).status_code == 200


@pytest.mark.xfail(
    strict=False,
    reason=(
        "R9: /api/system/scan 端点内部 enrich_metadata -> heal_all 使用 AsyncSessionLocal"
        " 而非调用方传入的 db, CI 上 DATABASE_URL=:memory: 为全新空库(无 songs 表),"
        " 查询抛 OperationalError -> 500。真实部署(有文件库)下正常。"
        " TODO: heal_all 支持注入 session 后移除本标记。"
    ),
)
async def test_known_broken_system_scan(smoke_client):
    # 端点已在 app/api/v1/scan.py 实现 (trigger_library_scan)
    assert (await smoke_client.post("/api/system/scan")).status_code == 200


@pytest.mark.xfail(
    strict=True,
    reason="R9: 端点拼 job_{source}，实际注册的是 job_new_release_check，恒 404",
)
async def test_known_broken_manual_check(smoke_client):
    assert (await smoke_client.post("/api/check/netease")).status_code == 200


@pytest.mark.xfail(strict=True, reason="R9: notifiers 包不存在，telegram 通道全线 ImportError")
async def test_known_broken_telegram_notify(smoke_client):
    assert (await smoke_client.post("/api/test_notify/telegram")).status_code == 200


@pytest.mark.xfail(
    strict=True, reason="R3: task_monitor 状态在内存，未知 task_id 也返回成功"
)
async def test_known_broken_task_pause_unknown_id(smoke_client):
    resp = await smoke_client.post("/api/tasks/definitely-not-a-task/pause")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [("get", "/api/search_songs"), ("post", "/api/repair_audio")],
)
@pytest.mark.xfail(strict=True, reason="R9: RepairModal.vue 调用的端点后端从未实现")
async def test_known_broken_repair_modal_endpoints(smoke_client, method, path):
    resp = await getattr(smoke_client, method)(path)
    # GET 版被 SPA catch-all 吞成 200 HTML，POST 版是 405——两者都不是可用的 JSON 端点
    assert resp.status_code < 400
    assert resp.headers.get("content-type", "").startswith("application/json")


async def test_known_broken_unknown_api_path_returns_html(smoke_client):
    resp = await smoke_client.get("/api/definitely-not-an-endpoint")
    assert resp.status_code == 404
