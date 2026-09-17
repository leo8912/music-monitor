# -*- coding: utf-8 -*-
"""
arq worker 入口 (阶段 3 / R3)

独立进程消费 Redis 队列中的任务。由 supervisord 托管 (scripts/supervisord.conf)。
仅在 MM_REDIS__ENABLED=true 时生效; inline 模式无需启动本进程。

启动: python -m app.workers.worker
"""
import logging
import os
import sys
import time
import traceback

def _write_err(msg):
    try:
        with open("/tmp/worker.err.log", "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass

try:
    from arq import cron
    from arq.connections import RedisSettings
    from arq.worker import Worker

    from core.settings import load_settings
    from app.workers import tasks  # noqa: F401  (导入即注册所有任务)
    from core.queue import _TASK_REGISTRY
except Exception as e:
    _write_err(f"IMPORT ERROR: {e}")
    _write_err(traceback.format_exc())
    raise

logger = logging.getLogger(__name__)

REDIS_SOCKET_WAIT_TIMEOUT = 30


def _redis_settings() -> RedisSettings:
    settings = load_settings().redis
    if settings.unix_socket:
        if os.path.exists(settings.unix_socket):
            logger.info(f"Using Redis unix socket: {settings.unix_socket}")
            return RedisSettings(unix_socket_path=settings.unix_socket)
        logger.warning(f"Redis unix socket {settings.unix_socket} not found, falling back to TCP")
    return RedisSettings.from_dsn(settings.url)


def _wait_for_redis():
    settings = load_settings().redis
    if not settings.unix_socket:
        return
    deadline = time.time() + REDIS_SOCKET_WAIT_TIMEOUT
    while time.time() < deadline:
        if os.path.exists(settings.unix_socket):
            return
        time.sleep(0.5)
    logger.error(f"Timeout waiting for Redis socket {settings.unix_socket}")


async def startup(ctx):
    logger.info("arq worker 启动")


async def shutdown(ctx):
    logger.info("arq worker 关闭")


def _cron_jobs():
    """周期任务: 与 APScheduler 的 3 个定时任务保持一致。"""
    return [
        cron(tasks.release_check, minute=0, hour=0, run_at_startup=False),
        cron(tasks.release_check, minute=0, hour=6, run_at_startup=False),
        cron(tasks.release_check, minute=0, hour=12, run_at_startup=False),
        cron(tasks.release_check, minute=0, hour=18, run_at_startup=False),
        cron(tasks.file_integrity, hour=3, minute=17),
        cron(tasks.asset_localize, hour=4, minute=23),
    ]


def main():
    logging.basicConfig(level=logging.INFO)

    # Redis 未启用时优雅退出 (supervisord 以 exitcode=0 不重启)
    from core.queue import is_arq_enabled
    if not is_arq_enabled():
        logger.info("arq worker 退出: Redis 未启用 (MM_REDIS__ENABLED=false)")
        return

    _wait_for_redis()

    worker = Worker(
        functions=[*_TASK_REGISTRY.values()],
        cron_jobs=_cron_jobs(),
        redis_settings=_redis_settings(),
        max_jobs=4,
        max_tries=3,
        job_timeout=3600,
        keep_result=3600,
        on_startup=startup,
        on_shutdown=shutdown,
    )
    worker.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _write_err(f"MAIN ERROR: {e}")
        _write_err(traceback.format_exc())
        raise
