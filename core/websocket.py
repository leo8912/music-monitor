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
        self._redis_client = None  # 缓存 Redis 客户端，避免每次广播创建新连接
        self._pubsub = None        # 缓存 pubsub 对象，重连时可先 unsubscribe
        try:
            from core.queue import is_arq_enabled
            self._use_redis = is_arq_enabled()
        except Exception:
            self._use_redis = False

    async def _get_redis(self):
        """获取或创建缓存的 redis.asyncio 客户端 (仅 arq 模式调用)。"""
        if self._redis_client is not None:
            return self._redis_client
        from redis.asyncio import Redis
        from core.settings import load_settings
        cfg = load_settings().redis
        if cfg.unix_socket and cfg.unix_socket.startswith("/"):
            self._redis_client = Redis.from_url(f"unix://{cfg.unix_socket}", decode_responses=True)
        else:
            self._redis_client = Redis.from_url(cfg.url, decode_responses=True)
        return self._redis_client

    async def connect(self, websocket: WebSocket):
        import asyncio
        await websocket.accept()
        self.active_connections.append(websocket)
        # 首个连接时启动 Redis 订阅转发协程 (幂等)
        if self._use_redis and self._pubsub_task is None:
            self._pubsub_task = asyncio.create_task(self._redis_pubsub_loop())
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
                # 连接可能已断开，清除缓存以便下次重连
                self._redis_client = None

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
        # 启动等待: 容器内 Redis (supervisord 管理) 可能尚在初始化,
        # 等待数秒避免首轮连接立即失败触发 WARNING 告警。
        await asyncio.sleep(3)
        _retries = 0
        _backoff_base = 5          # 初始退避 5s
        _backoff_max = 60          # 最大退避 60s
        while True:
            try:
                r = await self._get_redis()
                pubsub = r.pubsub()
                self._pubsub = pubsub
                await pubsub.subscribe(_WS_CHANNEL)
                _retries = 0        # 连接成功, 重置退避计数
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
                # 连接断开时清除缓存，下次循环重建
                self._redis_client = None
                self._pubsub = None
                _retries += 1
                delay = min(_backoff_base * (2 ** (_retries - 1)), _backoff_max)
                if _retries <= 3:
                    logger.info(
                        f"WS Redis pubsub 连接失败 (第{_retries}次), "
                        f"{delay}s 后重试: {e}"
                    )
                else:
                    logger.warning(
                        f"WS Redis pubsub 连续失败 (第{_retries}次), "
                        f"{delay}s 后重试: {e}"
                    )
                await asyncio.sleep(delay)

    async def disconnect_all(self):
        """关闭所有活动连接并释放 Redis 资源"""
        if self._pubsub_task is not None:
            self._pubsub_task.cancel()
            self._pubsub_task = None
        # 先 unsubscribe 再关闭连接
        if self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe(_WS_CHANNEL)
                await self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None
        # 关闭 Redis 客户端连接池
        if self._redis_client is not None:
            try:
                await self._redis_client.close()
            except Exception:
                pass
            self._redis_client = None
        for connection in self.active_connections[:]:  # 创建副本以避免在迭代时修改列表
            try:
                await connection.close()
            except Exception:
                pass  # 连接可能已经关闭
        self.active_connections.clear()

manager = ConnectionManager()
