import logging
import uuid
import time
import asyncio
import json
from typing import Dict, Optional, Any
from core.websocket import manager

logger = logging.getLogger(__name__)

# Redis 键前缀 (仅 arq 模式使用)
_TASK_KEY = "mm:task:{task_id}"
_CTL_KEY = "mm:taskctl:{task_id}"
_CTL_TTL = 86400  # 控制标志保留 24h, 防止孤儿键


class TaskMonitor:
    """
    Global Task Monitor Service

    Manages the lifecycle of background tasks and broadcasts updates via WebSocket.
    双模式状态存储 (阶段 3.4):
      - inline 模式 (默认/测试): 进程内 dict + asyncio.Event 控制, 无外部依赖。
      - arq 模式 (Redis): 任务状态写入 Redis (mm:task:{id}),
        暂停/取消标志写入 Redis (mm:taskctl:{id}), 供 worker 进程跨进程感知。
    Singleton pattern usage recommended.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.tasks = {}
        self._pause_events = {}  # task_id -> asyncio.Event
        self._cancel_flags = set() # task_id set

        # 惰性加载: 仅 arq 模式创建 Redis 客户端 (避免测试/无 Redis 环境失败)
        self._redis = None
        self._use_redis = False
        try:
            from core.queue import is_arq_enabled
            self._use_redis = is_arq_enabled()
        except Exception:
            self._use_redis = False

        self._initialized = True

    # --- Redis 后端 (arq 模式) ---

    async def _get_redis(self):
        """惰性创建 redis.asyncio 客户端 (仅 arq 模式调用)。"""
        if self._redis is None:
            from redis.asyncio import Redis
            from core.settings import load_settings
            cfg = load_settings().redis
            if cfg.unix_socket and cfg.unix_socket.startswith("/"):
                self._redis = Redis.from_url(f"unix://{cfg.unix_socket}", decode_responses=True)
            else:
                self._redis = Redis.from_url(cfg.url, decode_responses=True)
        return self._redis

    async def _redis_save_task(self, task_data: Dict):
        """arq 模式: 任务状态写入 Redis hash + TTL。"""
        if not self._use_redis:
            return
        try:
            r = await self._get_redis()
            payload = {
                "taskId": task_data.get("taskId", ""),
                "taskType": task_data.get("taskType", ""),
                "state": task_data.get("state", "running"),
                "progress": task_data.get("progress", 0),
                "message": task_data.get("message", ""),
                "details": json.dumps(task_data.get("details", {}), ensure_ascii=False),
                "timestamp": task_data.get("timestamp", 0),
            }
            await r.hset(_TASK_KEY.format(task_id=task_data.get("taskId", "")), mapping=payload)
            await r.expire(_TASK_KEY.format(task_id=task_data.get("taskId", "")), _CTL_TTL)
        except Exception as e:
            logger.warning(f"TaskMonitor: Redis 保存任务状态失败: {e}")

    async def _redis_get_ctl(self, task_id: str) -> Dict[str, bool]:
        """arq 模式: 读取暂停/取消标志。"""
        if not self._use_redis:
            return {"paused": False, "cancelled": False}
        try:
            r = await self._get_redis()
            raw = await r.hgetall(_CTL_KEY.format(task_id=task_id))
            return {
                "paused": raw.get("paused") == "1",
                "cancelled": raw.get("cancelled") == "1",
            }
        except Exception as e:
            logger.warning(f"TaskMonitor: Redis 读取控制标志失败: {e}")
            return {"paused": False, "cancelled": False}

    async def _redis_set_ctl(self, task_id: str, paused: Optional[bool] = None,
                             cancelled: Optional[bool] = None):
        """arq 模式: 写入暂停/取消标志。"""
        if not self._use_redis:
            return
        try:
            r = await self._get_redis()
            key = _CTL_KEY.format(task_id=task_id)
            if paused is not None:
                await r.hset(key, "paused", "1" if paused else "0")
            if cancelled is not None:
                await r.hset(key, "cancelled", "1" if cancelled else "0")
            await r.expire(key, _CTL_TTL)
        except Exception as e:
            logger.warning(f"TaskMonitor: Redis 写入控制标志失败: {e}")

    # --- 生命周期 ---

    async def start_task(
        self,
        task_type: str,
        message: str = "Starting...",
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new task and broadcast pending state.
        Returns: task_id (str)
        """
        task_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)

        task_data = {
            "taskId": task_id,
            "taskType": task_type,
            "state": "running",
            "progress": 0,
            "message": message,
            "details": details or {},
            "timestamp": timestamp
        }

        self.tasks[task_id] = task_data

        # Initialize control primitives
        self._pause_events[task_id] = asyncio.Event()
        self._pause_events[task_id].set() # Initially running (not paused)

        await self._redis_save_task(task_data)
        await self._broadcast(task_data)
        logger.info(f"Task Started [{task_type}]: {message} (ID: {task_id})")
        return task_id

    async def update_progress(
        self,
        task_id: str,
        progress: int,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        state: str = "running"
    ):
        """
        Update task progress and broadcast.
        """
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task["progress"] = progress
        if message:
            task["message"] = message
        if details:
            if "details" not in task:
                task["details"] = {}
            task["details"].update(details)

        # Don't overwrite state if it's already 'paused' or 'cancelling' unless explicitly finishing
        current_state = task.get("state", "running")
        if state == "running" and current_state in ["paused", "cancelling"]:
             pass # Keep current specific state
        else:
             task["state"] = state

        task["timestamp"] = int(time.time() * 1000)

        await self._redis_save_task(task)
        await self._broadcast(task)

    async def finish_task(self, task_id: str, message: str = "Completed", details: Optional[Dict] = None):
        """
        Mark task as completed and broadcast.
        """
        await self.update_progress(task_id, 100, message, details, state="completed")
        self._cleanup_task(task_id)
        logger.info(f"Task Completed (ID: {task_id})")

    async def error_task(self, task_id: str, error_message: str):
        """
        Mark task as error and broadcast.
        """
        await self.update_progress(task_id, self.tasks.get(task_id, {}).get("progress", 0), error_message, state="error")
        self._cleanup_task(task_id)
        logger.error(f"Task Failed (ID: {task_id}): {error_message}")

    # --- Control Methods ---

    async def pause_task(self, task_id: str):
        await self._redis_set_ctl(task_id, paused=True)
        if task_id in self._pause_events:
            self._pause_events[task_id].clear() # Will block wait()
            await self.update_progress(task_id, self._get_progress(task_id), state="paused")
            logger.info(f"Task Paused: {task_id}")

    async def resume_task(self, task_id: str):
        await self._redis_set_ctl(task_id, paused=False)
        if task_id in self._pause_events:
            self._pause_events[task_id].set() # Unblock
            await self.update_progress(task_id, self._get_progress(task_id), state="running")
            logger.info(f"Task Resumed: {task_id}")

    async def cancel_task(self, task_id: str):
        await self._redis_set_ctl(task_id, cancelled=True)
        if task_id in self.tasks:
            self._cancel_flags.add(task_id)
            # Ensure not paused so it can wake up and cancel
            if task_id in self._pause_events:
                self._pause_events[task_id].set()

            await self.update_progress(task_id, self._get_progress(task_id), state="cancelling")
            logger.info(f"Task Cancellation Requested: {task_id}")

    async def check_status(self, task_id: str):
        """
        Called by worker loops.
        1. Checks if cancelled -> Raises TaskCancelledException
        2. Checks if paused -> Waits until resumed
        跨进程 (arq 模式): 通过 Redis 控制标志感知 API 进程发起的暂停/取消。
        """
        if not task_id:
            return

        # arq 模式: 读 Redis 控制标志 (worker 进程与 API 进程分离)
        if self._use_redis:
            while True:
                ctl = await self._redis_get_ctl(task_id)
                if ctl.get("cancelled"):
                    raise TaskCancelledException(f"Task {task_id} cancelled by user")
                if ctl.get("paused"):
                    await asyncio.sleep(1)
                    continue
                return

        # inline 模式: 内存控制
        # Check cancellation
        if task_id in self._cancel_flags:
            raise TaskCancelledException(f"Task {task_id} cancelled by user")

        # Check pause (Wait if cleared)
        if task_id in self._pause_events:
            await self._pause_events[task_id].wait()

    def _cleanup_task(self, task_id: str):
        if task_id in self._pause_events:
            del self._pause_events[task_id]
        if task_id in self._cancel_flags:
            self._cancel_flags.remove(task_id)

    def _get_progress(self, task_id: str) -> int:
        return self.tasks.get(task_id, {}).get("progress", 0)

    async def _broadcast(self, task_data: Dict):
        """
        Construct WS message and send.
        """
        msg = {
            "type": "task_progress",
            "data": task_data
        }
        await manager.broadcast(msg)

class TaskCancelledException(Exception):
    pass

# Global Instance
task_monitor = TaskMonitor()
