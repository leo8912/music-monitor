# -*- coding: utf-8 -*-
"""
arq worker 入口 (阶段 3 / R3)

独立进程消费 Redis 队列中的任务。由 supervisord 托管 (scripts/supervisord.conf)。
仅在 MM_REDIS__ENABLED=true 时生效; inline 模式无需启动本进程。

启动: python -m app.workers.worker
"""
import logging

from arq import cron
from arq.connections import RedisSettings
from arq.worker import Worker

from core.settings import load_settings
from app.workers import tasks  # noqa: F401  (导入即注册所有任务)
from core.queue import _TASK_REGISTRY

logger = logging.getLogger(__name__)


def _redis_settings() -> RedisSettings:
    settings = load_settings().redis
    if settings.unix_socket:
        import os
        if os.path.exists(settings.unix_socket):
            return RedisSettings(host=settings.unix_socket)
    return RedisSettings.from_dsn(settings.url)


async def startup(ctx):
    logger.info("arq worker 启动")


async def shutdown(ctx):
    logger.info("arq worker 关闭")


def _cron_jobs():
    """周期任务: 与 APScheduler 的 3 个定时任务保持一致。"""
    return [
        cron(tasks.release_check, minute=0, hour="*/6", run_at_startup=False),
        cron(tasks.file_integrity, hour=3, minute=17),
        cron(tasks.asset_localize, hour=4, minute=23),
    ]


def main():
    logging.basicConfig(level=logging.INFO)
    worker = Worker(
        functions=[*_TASK_REGISTRY.values()],
        cron_jobs=_cron_jobs(),
        redis_settings=_redis_settings(),
        max_jobs=4,
        job_timeout=3600,
        keep_result=3600,
        on_startup=startup,
        on_shutdown=shutdown,
    )
    worker.run()


if __name__ == "__main__":
    main()
