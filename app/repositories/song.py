from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from app.models.song import Song
from app.repositories.base import BaseRepository

class SongRepository(BaseRepository[Song]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Song)

    async def get(self, id: int) -> Optional[Song]:
        stmt = select(self._model).options(joinedload(Song.artist)).where(self._model.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[dict] = None
    ) -> List[Song]:
        """Overwrite get_multi to add default sorting by created_at desc"""
        stmt = select(self._model).options(joinedload(Song.artist))
        
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(self._model, key) == value)
        
        # Default sort by created_at desc if available
        if hasattr(self._model, 'created_at'):
            stmt = stmt.order_by(self._model.created_at.desc())
            
        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_unique_key(self, source: str, source_id: str) -> Optional[Song]:
        """
        根据来源和ID获取歌曲
        Queries SongSource to find the parent Song.
        """
        from app.models.song import SongSource
        stmt = (
            select(Song)
            .join(SongSource)
            .options(joinedload(Song.artist))
            .where(
                and_(SongSource.source == source, SongSource.source_id == source_id)
            )
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_path(self, path: str) -> Optional[Song]:
        """根据路径获取歌曲"""
        stmt = select(Song).options(joinedload(Song.artist)).where(Song.local_path == path)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_title_artist(self, title: str, artist: str) -> Optional[Song]:
        """根据标题和艺术家获取歌曲"""
        stmt = select(Song).options(joinedload(Song.artist)).where(
            and_(Song.title == title, Song.artist_id == artist)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_favorites(self, skip: int = 0, limit: int = 100) -> List[Song]:
        """获取收藏歌曲"""
        stmt = select(Song).options(joinedload(Song.artist)).where(Song.is_favorite == True).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def toggle_favorite(self, song_id: int) -> Optional[Song]:
        """切换收藏状态"""
        song = await self.get(song_id)
        if song:
            song.is_favorite = not song.is_favorite
            await self._session.commit()
            await self._session.refresh(song)
        return song


    async def get_by_artist(self, artist_id: int, skip: int = 0, limit: int = 100) -> List[Song]:
        """根据艺术家ID获取歌曲"""
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Song)
            .options(
                selectinload(Song.artist),
                selectinload(Song.sources)
            )
            .where(Song.artist_id == artist_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        artist_name: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        only_monitored: bool = False,
        sort_by: str = "publish_time",
        order: str = "desc"
    ) -> Tuple[List[Song], int]:
        """
        分页获取歌曲，支持过滤、去重和排序
        """
        from sqlalchemy import func, desc, asc, text
        from app.models.artist import Artist
        
        # 1. 构造过滤子查询 (用于去重和计数)
        # 我们使用 (title, artist_id) 作为去重键
        # 选取每个组中 id 最小的那个作为代表
        filter_stmt = select(
            Song.title,
            Song.artist_id,
            func.min(Song.id).label("min_id")
        )

        # Filters
        if artist_name or only_monitored:
             filter_stmt = filter_stmt.join(Song.artist)
             
        if artist_name:
            filter_stmt = filter_stmt.where(Artist.name.ilike(f"%{artist_name}%"))
        
        if is_favorite is not None:
             filter_stmt = filter_stmt.where(Song.is_favorite == is_favorite)

        if only_monitored:
            filter_stmt = filter_stmt.where(Artist.is_monitored == True)

        filter_stmt = filter_stmt.group_by(Song.title, Song.artist_id)
        
        # 2. 获取去重后的总数
        count_stmt = select(func.count()).select_from(filter_stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar() or 0

        # 3. 构造主查询获取完整对象
        distinct_ids_stmt = select(filter_stmt.subquery().c.min_id)
        
        # 主查询
        stmt = select(Song).options(joinedload(Song.artist)).where(Song.id.in_(distinct_ids_stmt))
        
        # 4. 处理排序
        order_func = desc if order.lower() == "desc" else asc
        if sort_by == "publish_time":
            stmt = stmt.order_by(order_func(Song.publish_time).nullslast(), order_func(Song.created_at))
        elif sort_by == "created_at":
            stmt = stmt.order_by(order_func(Song.created_at))
        elif sort_by == "title":
            stmt = stmt.order_by(order_func(Song.title))
        elif sort_by == "artist":
            # 关联 Artist 表并按名称排序
            stmt = stmt.join(Artist).order_by(order_func(Artist.name))
        elif sort_by == "album":
            stmt = stmt.order_by(order_func(Song.album))
        else:
            # 默认排序
            stmt = stmt.order_by(Song.publish_time.desc().nullslast(), Song.created_at.desc())
        
        # 5. 分页
        stmt = stmt.offset(skip).limit(limit)
        
        # 6. 加载来源并执行
        from sqlalchemy.orm import selectinload
        stmt = stmt.options(selectinload(Song.sources))
        result = await self._session.execute(stmt)
        songs = result.scalars().all()
        
        return songs, total
