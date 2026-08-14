from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket import manager
from core.config_manager import get_config_manager

router = APIRouter()


@router.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    # 鉴权: 与 app.dependencies.require_auth 语义一致 ——
    # auth.enabled=True 时要求会话中已登录, 否则以 4401 (未授权) 关闭连接,
    # 避免匿名客户端订阅进度广播 (下载/扫描/补全等敏感事件)。
    auth_cfg = get_config_manager().get('auth', {})
    if auth_cfg.get('enabled', False):
        session = websocket.scope.get("session") or {}
        if not session.get("user"):
            await websocket.close(code=4401)
            return

    await manager.connect(websocket)
    try:
        while True:
            # We just need to keep the connection open.
            # Client might send "ping" or nothing.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        # Handle unexpected disconnects
        manager.disconnect(websocket)
