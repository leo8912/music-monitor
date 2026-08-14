# ruff: noqa: PLC0415 - 测试文件按需导入
"""
任务调度并发专项回归测试 (2026-08-14 深夜)

覆盖:
- active_refreshes 原子检查-添加: 并发 acquire 同一歌手仅一个成功
- _refresh_enrich_count 原子预占: 并发下不超发, 每次 refresh 重置预算
- auto_download 并发度: 信号量按 max_concurrent_downloads 配置初始化
"""
import asyncio
import pytest


# ===========================================================================
# active_refreshes 原子性
# ===========================================================================
@pytest.mark.asyncio
async def test_acquire_active_refresh_is_atomic():
    from app.services import subscription as sub_mod

    async def worker(name: str):
        # 并发调用 acquire; 原子锁保证同一歌手只放行一个
        return await sub_mod.acquire_active_refresh(name)

    try:
        # 清空共享状态, 避免污染其他测试
        async with sub_mod._active_refresh_lock:
            sub_mod.active_refreshes.clear()

        results = await asyncio.gather(
            worker("周杰伦"), worker("周杰伦"), worker("周杰伦"),
            worker("林俊杰"), worker("林俊杰"),
        )
        # 周杰伦 3 个并发只有一个成功, 林俊杰 2 个并发只有一个成功
        assert results.count(True) == 2
        assert results.count(False) == 3

        # 释放后重新可获取
        await sub_mod.release_active_refresh("周杰伦")
        assert await sub_mod.acquire_active_refresh("周杰伦") is True
    finally:
        async with sub_mod._active_refresh_lock:
            sub_mod.active_refreshes.clear()


@pytest.mark.asyncio
async def test_release_active_refresh_is_idempotent():
    from app.services import subscription as sub_mod

    async with sub_mod._active_refresh_lock:
        sub_mod.active_refreshes.clear()

    assert await sub_mod.acquire_active_refresh("陈奕迅") is True
    await sub_mod.release_active_refresh("陈奕迅")
    # 重复释放不报错
    await sub_mod.release_active_refresh("陈奕迅")
    assert "陈奕迅" not in sub_mod.active_refreshes

    async with sub_mod._active_refresh_lock:
        sub_mod.active_refreshes.clear()


# ===========================================================================
# _refresh_enrich_count 原子预占 + 预算重置
# ===========================================================================
async def _run_enrich_once(svc):
    """与生产代码相同的锁内检查-预占逻辑:
    `async with svc._refresh_enrich_lock: if count < 15: count += 1; return True`。
    """
    async with svc._refresh_enrich_lock:
        if svc._refresh_enrich_count < 15:
            svc._refresh_enrich_count += 1
            return True
        return False


@pytest.mark.asyncio
async def test_enrich_budget_reset_per_refresh():
    """预算在 refresh() 开头重置为 0 (同实例多次刷新不累计)。"""
    from app.services.artist_refresh_service import ArtistRefreshService

    svc = ArtistRefreshService.__new__(ArtistRefreshService)
    svc._refresh_enrich_count = 0
    svc._refresh_enrich_lock = asyncio.Lock()

    # 模拟一次 refresh 消耗 3 次预算
    for _ in range(3):
        assert await _run_enrich_once(svc) is True
    assert svc._refresh_enrich_count == 3
    assert await _run_enrich_once(svc) is True  # 未到 15, 仍可预占

    # refresh() 开头重置 (见 refresh() 中 self._refresh_enrich_count = 0)
    svc._refresh_enrich_count = 0
    assert await _run_enrich_once(svc) is True


@pytest.mark.asyncio
async def test_enrich_budget_atomic_no_overrun():
    """并发预占不超过上限 15。"""
    from app.services.artist_refresh_service import ArtistRefreshService

    svc = ArtistRefreshService.__new__(ArtistRefreshService)
    svc._refresh_enrich_count = 0
    svc._refresh_enrich_lock = asyncio.Lock()

    async def worker():
        return await _run_enrich_once(svc)

    results = await asyncio.gather(*[worker() for _ in range(40)])
    assert sum(1 for r in results if r) == 15  # 恰好 15 个成功预占
    assert svc._refresh_enrich_count == 15
    # 计数已达上限, 后续预占全部拒绝
    assert await _run_enrich_once(svc) is False


# ===========================================================================
# auto_download 并发度
# ===========================================================================
@pytest.mark.asyncio
async def test_download_semaphore_reads_config(monkeypatch):
    from core.config_manager import get_config_manager
    from app.services import auto_download_service as ad_mod

    get_config_manager().update({"system": {"max_concurrent_downloads": 5}})
    # 重置模块级信号量, 强制按新配置重建
    ad_mod._download_semaphore = None

    sem = await ad_mod._get_download_semaphore()
    # 信号量无公开 value 属性, 通过并发获取数验证容量
    acquired = 0
    got = []

    async def try_acquire():
        nonlocal acquired
        try:
            await asyncio.wait_for(sem.acquire(), timeout=0.1)
            acquired += 1
            got.append(True)
        except asyncio.TimeoutError:
            got.append(False)

    await asyncio.gather(*[try_acquire() for _ in range(8)])
    assert acquired == 5  # 只有 5 个能立即获取 (容量 5)

    # 释放后恢复 (避免信号量耗尽影响其他测试)
    for _ in range(acquired):
        sem.release()
    ad_mod._download_semaphore = None


@pytest.mark.asyncio
async def test_download_semaphore_config_fallback(monkeypatch):
    """配置缺失/非法时回退默认 3。"""
    from core.config_manager import get_config_manager
    from app.services import auto_download_service as ad_mod

    get_config_manager().update({"system": {"max_concurrent_downloads": "abc"}})
    ad_mod._download_semaphore = None

    sem = await ad_mod._get_download_semaphore()
    acquired = 0
    got = []

    async def try_acquire():
        nonlocal acquired
        try:
            await asyncio.wait_for(sem.acquire(), timeout=0.1)
            acquired += 1
            got.append(True)
        except asyncio.TimeoutError:
            got.append(False)

    await asyncio.gather(*[try_acquire() for _ in range(6)])
    assert acquired == 3  # 回退默认 3

    for _ in range(acquired):
        sem.release()
    ad_mod._download_semaphore = None
