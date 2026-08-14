import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Redis pubsub 频道 (仅 arq 模式使用): worker 进程通过该频道广播事件,
# API 进程订阅并转发给本地 WebSocket 客户端。
_WS_CHANNEL = "mm:ws"


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._use_redis = False
        self._pubsub_task = None
        try:
            from core.queue import is_arq_enabled
            self._use_redis = is_arq_enabled()
        except Exception:
            self._use_redis = False

    async def _get_redis(self):
        """惰性创建 redis.asyncio 客户端 (仅 arq 模式调用)。"""
        from redis.asyncio import Redis
        from core.settings import load_settings
        cfg = load_settings().redis
        if cfg.unix_socket and cfg.unix_socket.startswith("/"):
            return Redis.from_url(f"unix://{cfg.unix_socket}", decode_responses=True)
        return Redis.from_url(cfg.url, decode_responses=True)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # 首个连接时启动 Redis 订阅转发协程 (幂等)
        if self._use_redis and self._pubsub_task is None:
            self._pubsub_task = __import__("asyncio").create_task(self._redis_pubsub_loop())
        logger.info(f"WS Connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WS Disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # arq 模式: 先发布到 Redis 频道 (worker 进程事件经此到达本进程)
        if self._use_redis:
            try:
                import json
                r = await self._get_redis()
                await r.publish(_WS_CHANNEL, json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.warning(f"WS Redis publish failed: {e}")

        if not self.active_connections:
            logger.debug(f"No active WS connections (skip broadcast): {message.get('type', message)}")
            return

        logger.debug(f"Broadcasting to {len(self.active_connections)} clients: {message.get('message', '')}")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

    async def _redis_pubsub_loop(self):
        """arq 模式: 订阅 Redis 频道, 将 worker 进程广播的事件转发给本地 WS 客户端。"""
        import asyncio
        import json
        logger.info("WS Redis pubsub subscriber started")
        while True:
            try:
                r = await self._get_redis()
                pubsub = r.pubsub()
                await pubsub.subscribe(_WS_CHANNEL)
                async for msg in pubsub.listen():
                    if msg.get("type") != "message":
                        continue
                    try:
                        payload = json.loads(msg["data"])
                    except Exception:
                        continue
                    for connection in list(self.active_connections):
                        try:
                            await connection.send_json(payload)
                        except Exception:
                            pass
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"WS Redis pubsub loop error, retrying: {e}")
                await asyncio.sleep(5)

    async def disconnect_all(self):
        """关闭所有活动连接"""
        if self._pubsub_task is not None:
            self._pubsub_task.cancel()
            self._pubsub_task = None
        for connection in self.active_connections[:]:  # 创建副本以避免在迭代时修改列表
            try:
                await connection.close()
            except Exception:
                pass  # 连接可能已经关闭
        self.active_connections.clear()

manager = ConnectionManager()
