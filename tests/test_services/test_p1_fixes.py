# ruff: noqa: PLC0415 - 测试文件按需导入, 避免拖慢收集
"""
🟡 中等问题修复回归测试 (2026-08-14 晚)

覆盖:
- M2: WS /ws/progress 鉴权 (auth.enabled=True 时未登录以 4401 关闭)
- M3: 密码哈希 (pbkdf2) + 登录失败限速
- M5: queue._is_locked_error 异常链健壮化 (PendingRollbackError/DBAPI orig)
"""
import types
import pytest
from fastapi import HTTPException, WebSocketDisconnect


# ===========================================================================
# M2: WS 鉴权
# ===========================================================================
class _FakeWebSocket:
    def __init__(self, session):
        # session 为 None 表示 scope 无 session 键 (匿名连接)
        self.scope = {"session": session} if session is not None else {}
        self.closed_code = None
        self.accepted = False

    async def close(self, code=1000):
        self.closed_code = code

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        raise WebSocketDisconnect()


class _FakeManager:
    def __init__(self):
        self.connected = None
        self.disconnected = None

    async def connect(self, ws):
        self.connected = ws
        # 模拟真实 ConnectionManager.connect: accept 后才加入连接池
        await ws.accept()

    def disconnect(self, ws):
        self.disconnected = ws


@pytest.mark.asyncio
async def test_ws_progress_rejects_anonymous_when_auth_enabled(monkeypatch):
    from core.config_manager import get_config_manager
    from app.api.v1.websocket import websocket_endpoint

    get_config_manager().update({"auth": {"enabled": True}})
    fake_mgr = _FakeManager()
    monkeypatch.setattr("app.api.v1.websocket.manager", fake_mgr)

    ws = _FakeWebSocket(session=None)
    await websocket_endpoint(ws)

    assert ws.closed_code == 4401  # 未授权
    assert ws.accepted is False
    assert fake_mgr.connected is None


@pytest.mark.asyncio
async def test_ws_progress_accepts_logged_in_when_auth_enabled(monkeypatch):
    from core.config_manager import get_config_manager
    from app.api.v1.websocket import websocket_endpoint

    get_config_manager().update({"auth": {"enabled": True}})
    fake_mgr = _FakeManager()
    monkeypatch.setattr("app.api.v1.websocket.manager", fake_mgr)

    ws = _FakeWebSocket(session={"user": "admin"})
    await websocket_endpoint(ws)

    assert ws.accepted is True
    assert fake_mgr.connected is ws
    assert fake_mgr.disconnected is ws  # receive_text 抛 WebSocketDisconnect 后走 disconnect


@pytest.mark.asyncio
async def test_ws_progress_accepts_when_auth_disabled(monkeypatch):
    from core.config_manager import get_config_manager
    from app.api.v1.websocket import websocket_endpoint

    get_config_manager().update({"auth": {"enabled": False}})
    fake_mgr = _FakeManager()
    monkeypatch.setattr("app.api.v1.websocket.manager", fake_mgr)

    ws = _FakeWebSocket(session=None)
    await websocket_endpoint(ws)

    assert ws.accepted is True
    assert fake_mgr.connected is ws


# ===========================================================================
# M3: 密码哈希 + 登录限速
# ===========================================================================
def test_hash_password_roundtrip():
    from core.security import hash_password, verify_password

    h = hash_password("secret123")
    assert h.startswith("$pbkdf2-sha256$")
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)
    # 同密码不同盐 → 哈希不同 (随机盐)
    assert hash_password("secret123") != h


def test_verify_password_compat_plaintext():
    """旧版明文配置兼容 (常数时间比较)。"""
    from core.security import verify_password

    assert verify_password("plain", "plain")
    assert not verify_password("plain", "other")
    assert not verify_password("", "")


@pytest.mark.asyncio
async def test_login_success_and_rate_limit(monkeypatch):
    from app.schemas import LoginRequest
    from app.api.v1 import auth as auth_mod
    from core.config_manager import get_config_manager

    get_config_manager().update({
        "auth": {"enabled": True, "username": "admin", "password": "correct"}
    })
    auth_mod._LOGIN_FAILS.clear()

    request = types.SimpleNamespace(session={})

    # 连续 5 次错误密码 → 前 5 次 401 (第 5 次触发锁定)
    for _ in range(auth_mod._LOGIN_MAX_FAILS):
        with pytest.raises(HTTPException) as exc_info:
            await auth_mod.login(LoginRequest(username="admin", password="wrong"), request)
        assert exc_info.value.status_code == 401

    # 锁定期内即使密码正确也拒绝 (429)
    with pytest.raises(HTTPException) as exc_info:
        await auth_mod.login(LoginRequest(username="admin", password="correct"), request)
    assert exc_info.value.status_code == 429

    # 清理, 避免影响其他测试
    auth_mod._LOGIN_FAILS.clear()


@pytest.mark.asyncio
async def test_login_success_clears_failures(monkeypatch):
    from app.schemas import LoginRequest
    from app.api.v1 import auth as auth_mod
    from core.config_manager import get_config_manager

    get_config_manager().update({
        "auth": {"enabled": True, "username": "admin", "password": "correct"}
    })
    auth_mod._LOGIN_FAILS.clear()
    request = types.SimpleNamespace(session={})

    # 2 次失败后登录成功 → 计数清零, 不会触发锁定
    for _ in range(2):
        with pytest.raises(HTTPException):
            await auth_mod.login(LoginRequest(username="admin", password="wrong"), request)

    resp = await auth_mod.login(LoginRequest(username="admin", password="correct"), request)
    assert resp["success"] is True
    assert request.session == {"user": "admin"}
    assert auth_mod._LOGIN_FAILS == {}

    auth_mod._LOGIN_FAILS.clear()


# ===========================================================================
# M5: queue._is_locked_error 异常链健壮化
# ===========================================================================
@pytest.mark.asyncio
async def test_is_locked_error_plain_sqlite():
    from core.queue import _is_locked_error
    import sqlite3

    assert await _is_locked_error(sqlite3.OperationalError("database is locked"))
    assert await _is_locked_error(sqlite3.OperationalError("SQLITE_BUSY"))
    assert not await _is_locked_error(sqlite3.OperationalError("no such table"))


@pytest.mark.asyncio
async def test_is_locked_error_finds_dbapi_orig():
    """SQLAlchemy OperationalError 的 orig 是底层 sqlite3 异常。"""
    from core.queue import _is_locked_error
    from sqlalchemy.exc import OperationalError
    import sqlite3

    orig = sqlite3.OperationalError("database is locked")
    exc = OperationalError("SELECT 1", {}, orig)
    assert await _is_locked_error(exc)


@pytest.mark.asyncio
async def test_is_locked_error_finds_cause_chain():
    """包装异常 (如 PendingRollbackError 链) 沿 __cause__ 找原始锁冲突。"""
    from core.queue import _is_locked_error
    import sqlite3

    wrapped = RuntimeError("task failed, see cause")
    wrapped.__cause__ = sqlite3.OperationalError("database is locked")
    assert await _is_locked_error(wrapped)

    not_locked = RuntimeError("something else")
    not_locked.__cause__ = sqlite3.OperationalError("no such table")
    assert not await _is_locked_error(not_locked)
