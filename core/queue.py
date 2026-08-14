# -*- coding: utf-8 -*-
"""
任务队列抽象层 (阶段 3 / R3)

统一的后台任务投递接口，屏蔽底层实现差异：
- **arq 模式** (Redis 可用, MM_REDIS__ENABLED=true)：任务进入 Redis 队列，
  由独立 worker 进程 (app.workers.worker) 消费。支持持久化、重试、超时。
- **inline 模式** (默认, 本地开发/测试无 Redis)：任务以 asyncio.create_task
  在当前进程直接执行。功能等价，仅不具备跨进程/持久化能力。

用法:
    from core.queue import enqueue
    await enqueue("auto_download", snapshots=[...])
    await enqueue("heal_all", force=True, limit=50)

任务函数注册表见 app/workers/tasks.py (arq 模式 worker 使用同一注册表)。
"""
import asyncio
import logging
import os
from typing import Any, Dict, Optional

from core.settings import load_settings

logger = logging.getLogger(__name__)

# inline 模式最大并发任务数 (默认 8): 防止大量后台任务 (如一次刷新发现
# 上千首新歌) 同时持有 DB 会话/连接, 导致连接池耗尽 (QueuePool overflow)
_INLINE_MAX_CONCURRENCY = int(os.getenv("QUEUE_INLINE_CONCURRENCY", "8"))
# 3.10+ 的 asyncio.Semaphore 无需绑定事件循环, 可直接模块级创建
_inline_semaphore = asyncio.Semaphore(_INLINE_MAX_CONCURRENCY)


# SQLite 单写者锁冲突重试: 批量新歌发现时, 主事务未提交而多个后台任务
# 并发写库会触发 "database is locked" (OperationalError)。此常量控制
# _run_inline_task 对该错误的自动重试次数 (指数退避)。
_MAX_LOCKED_RETRIES = int(os.getenv("QUEUE_LOCKED_RETRIES", "3"))


async def _is_locked_error(e: Exception) -> bool:
    """判断异常是否为 SQLite 写锁冲突。

    仅凭 `str(e)` 匹配顶层异常消息过于脆弱: SQLAlchemy 在已失败事务上继续
    操作会抛 PendingRollbackError 等包装异常 (H4 修复前正是这类异常屏蔽了
    本重试逻辑)。因此沿异常链 (__cause__/__context__) 与 DBAPI orig 逐层
    检查, 只要任一层命中 "database is locked" / SQLITE_BUSY 即视为写锁冲突。
    """
    seen = set()
    cur: Exception | None = e
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        msg = str(cur)
        if "database is locked" in msg or "SQLITE_BUSY" in msg:
            return True
        # SQLAlchemy DBAPIError 用 .orig 保存底层驱动异常 (sqlite3.OperationalError)
        orig = getattr(cur, "orig", None)
        if orig is not None and id(orig) not in seen:
            seen.add(id(orig))
            orig_msg = str(orig)
            if "database is locked" in orig_msg or "SQLITE_BUSY" in orig_msg:
                return True
        cur = cur.__cause__ or cur.__context__
    return False


async def _run_inline_task(func, *args, **kwargs):
    """inline 模式下执行任务: 限流 + locked 重试 + 兜底异常记录。"""
    async with _inline_semaphore:
        for attempt in range(_MAX_LOCKED_RETRIES + 1):
            try:
                await func(*args, **kwargs)
                return
            except Exception as e:  # pragma: no cover
                if attempt < _MAX_LOCKED_RETRIES and await _is_locked_error(e):
                    delay = 1.5 * (2 ** attempt)
                    logger.warning(
                        f"Queue: 任务 {getattr(func, '__name__', func)} 遇 SQLite 写锁, "
                        f"第 {attempt + 1}/{_MAX_LOCKED_RETRIES} 次重试 ({delay:.1f}s 后): {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(
                    f"Queue: 后台任务 {getattr(func, '__name__', func)} 执行失败: {e}",
                    exc_info=True,
                )
                return

# 进程内唯一后台任务注册表 (job_name -> async callable)
# arq worker 与本进程 inline 执行共用，保证两种模式行为一致。
_TASK_REGISTRY: Dict[str, Any] = {}


def register_task(name: str):
    """装饰器: 将函数注册为可入队任务。"""
    def decorator(func):
        _TASK_REGISTRY[name] = func
        return func
    return decorator


def get_task(name: str):
    """按名称获取任务函数。"""
    return _TASK_REGISTRY.get(name)


def list_tasks() -> list:
    return sorted(_TASK_REGISTRY.keys())


def _redis_enabled() -> bool:
    """读取 Redis 是否启用 (仅启动时读取一次, 缓存模块级)。"""
    try:
        return bool(load_settings().redis.enabled)
    except Exception as e:
        logger.warning(f"读取 Redis 配置失败, 默认 inline 模式: {e}")
        return False


_USE_ARQ: bool = _redis_enabled()


def is_arq_enabled() -> bool:
    """当前是否运行在 arq (Redis) 模式。"""
    return _USE_ARQ


async def enqueue(job_name: str, *args, **kwargs) -> Optional[str]:
    """
    投递一个后台任务。

    Args:
        job_name: 注册表中的任务名
        *args/**kwargs: 透传给任务函数

    Returns:
        arq 模式返回 job_id (str); inline 模式返回 None。
    """
    # 惰性导入任务模块, 确保 API 进程也能投递任务 (幂等, 已导入则无副作用)
    if not _TASK_REGISTRY:
        try:
            from app.workers import tasks  # noqa: F401
        except Exception as e:  # pragma: no cover
            logger.warning(f"Queue: 任务模块导入失败: {e}")

    func = _TASK_REGISTRY.get(job_name)
    if func is None:
        logger.error(f"Queue: 未注册的任务 '{job_name}', 可用: {list_tasks()}")
        return None

    if _USE_ARQ:
        return await _enqueue_arq(job_name, *args, **kwargs)

    # inline 模式: 当前进程内后台执行 (信号量限流, 见 _run_inline_task)
    try:
        asyncio.create_task(_run_inline_task(func, *args, **kwargs))
    except RuntimeError as e:
        # 无运行中事件循环 (如同步上下文): 记录错误而非静默丢弃
        logger.error(f"Queue: inline 模式无事件循环, 任务 {job_name} 无法投递: {e}")
        return None
    return None


async def _enqueue_arq(job_name: str, *args, **kwargs) -> Optional[str]:
    """arq 模式: 写入 Redis 队列。"""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        settings = load_settings().redis
        if settings.unix_socket and _path_exists(settings.unix_socket):
            redis_settings = RedisSettings(host=settings.unix_socket)
        else:
            # url 形如 redis://host:port/db
            redis_settings = RedisSettings.from_dsn(settings.url)

        redis = await create_pool(redis_settings)
        try:
            job = await redis.enqueue_job(job_name, *args, **kwargs)
            job_id = job.job_id if job else None
            logger.info(f"Queue: 任务 {job_name} 已入队 (job_id={job_id})")
            return job_id
        finally:
            await redis.close()
    except Exception as e:
        logger.error(f"Queue: arq 入队失败, 任务 {job_name} 降级 inline: {e}")
        return None


def _path_exists(path: str) -> bool:
    import os
    return bool(path) and os.path.exists(path)


# 延迟导入 asyncio, 避免模块加载时绑定事件循环策略
import asyncio  # noqa: E402
