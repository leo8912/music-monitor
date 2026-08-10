# -*- coding: utf-8 -*-
"""
测试地基自检 (Meta-tests)

这几条用例不测业务，测的是 `conftest.py` 里 `db_session` 夹具本身。
它们存在的理由很实在：旧版夹具的隔离是**假的**（被测代码 commit 之后 rollback 无效），
一旦有人把 conftest 改回去，业务测试只会表现为"随机幽灵失败"，极难定位。
把隔离契约变成显式断言，退化就会在这里当场暴露。

Author: music-monitor QA
"""
import pytest
from sqlalchemy import func, select

from app.models.artist import Artist

LEAK_CANARY_NAME = "隔离哨兵-不应泄漏到其它测试"


@pytest.mark.asyncio
async def test_commit_does_not_escape_outer_transaction(db_session):
    """
    被测代码里到处是 `await session.commit()`。在 SAVEPOINT 方案下，
    这种 commit 只会 RELEASE SAVEPOINT，外层事务必须依然存活 ——
    只有这样 teardown 的 rollback 才能把数据整体抹掉。
    """
    db_session.add(Artist(name="事务存活检查"))
    await db_session.commit()

    conn = await db_session.connection()
    assert conn.in_transaction() is True, (
        "session.commit() 把外层事务也提交掉了，SAVEPOINT 隔离失效 —— "
        "请检查 conftest 中 db_session 是否绑定到了已开启事务的 Connection，"
        "以及 join_transaction_mode='create_savepoint' 是否生效。"
    )


@pytest.mark.asyncio
async def test_a_write_and_commit(db_session):
    """第一步：写入并 commit（模拟真实 service 的行为）。"""
    db_session.add(Artist(name=LEAK_CANARY_NAME))
    await db_session.commit()

    count = await db_session.scalar(
        select(func.count()).select_from(Artist).where(Artist.name == LEAK_CANARY_NAME)
    )
    assert count == 1


@pytest.mark.asyncio
async def test_b_previous_commit_is_invisible(db_session):
    """
    第二步：上一条用例 commit 的数据不得出现在这里。
    （用例按文件内顺序执行，本条必须排在 test_a_ 之后。）
    """
    count = await db_session.scalar(
        select(func.count()).select_from(Artist).where(Artist.name == LEAK_CANARY_NAME)
    )
    assert count == 0, "上一条用例的数据泄漏过来了，测试之间没有真正隔离"


@pytest.mark.asyncio
async def test_all_tables_created(db_session):
    """create_all 应建出全部 ORM 表，而不是只建"恰好被 import 过"的那几张。"""
    from app.models.base import Base

    expected = {"artists", "songs"}
    actual = set(Base.metadata.tables.keys())
    missing = expected - actual
    assert not missing, f"以下表未注册到 Base.metadata: {missing}（conftest 是否漏 import app.models？）"
