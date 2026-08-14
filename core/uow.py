"""
Unit of Work (UoW) Pattern Implementation

单元工作模式：
- 封装事务边界，所有数据库操作在单个事务内完成
- 自动提交（成功）或回滚（异常）
- 避免分散的 session.commit() 调用
- 支持嵌套上下文（SAVEPOINT）

使用示例：
```python
async def update_song(song_id: int, data: dict, db: AsyncSession):
    async with UnitOfWork(db) as uow:
        # 所有操作在这里进行
        song = await uow.songs.get(song_id)
        uow.songs.update(song, data)
        # 离开上下文时自动 commit（或在异常时 rollback）
```
"""

from typing import TYPE_CHECKING
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.repositories.song import SongRepository
    from app.repositories.artist import ArtistRepository
    from app.repositories.media_record import MediaRecordRepository


class UnitOfWork:
    """
    Unit of Work 实现：管理一个事务内的所有数据操作。

    在 async with 块退出时：
    - 如果没有异常，调用 commit()
    - 如果有异常，调用 rollback()
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._songs = None
        self._artists = None
        self._media_records = None

    @property
    def songs(self) -> "SongRepository":
        if self._songs is None:
            from app.repositories.song import SongRepository
            self._songs = SongRepository(self.session)
        return self._songs

    @property
    def artists(self) -> "ArtistRepository":
        if self._artists is None:
            from app.repositories.artist import ArtistRepository
            self._artists = ArtistRepository(self.session)
        return self._artists

    @property
    def media_records(self) -> "MediaRecordRepository":
        if self._media_records is None:
            from app.repositories.media_record import MediaRecordRepository
            self._media_records = MediaRecordRepository(self.session)
        return self._media_records

    async def commit(self):
        """提交当前事务"""
        await self.session.commit()

    async def rollback(self):
        """回滚当前事务"""
        await self.session.rollback()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 异常发生，回滚
            await self.rollback()
        else:
            # 正常完成，提交
            await self.commit()
        return False


@asynccontextmanager
async def transactional(session: AsyncSession):
    """
    便利装饰器：创建一个 UnitOfWork 上下文。

    使用示例：
    ```python
    async with transactional(db) as uow:
        uow.songs.create(...)
    ```
    """
    uow = UnitOfWork(session)
    async with uow:
        yield uow
