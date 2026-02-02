from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.artist import Artist
from app.repositories.base import BaseRepository

class ArtistRepository(BaseRepository[Artist]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Artist)

    async def get_by_name(self, name: str) -> Optional[Artist]:
        """根据名称获取艺术家"""
        stmt = select(Artist).where(Artist.name == name)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_source_and_id(self, source: str, source_id: str) -> Optional[Artist]:
        """根据来源和ID获取艺术家 (Query via ArtistSource)"""
        if source == "database": 
             return await self.get(int(source_id))

        from app.models.artist import ArtistSource
        stmt = (
            select(Artist)
            .join(ArtistSource)
            .where(
                and_(ArtistSource.source == source, ArtistSource.source_id == source_id)
            )
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()
    
    async def get_by_name_with_songs(self, name: str) -> Optional[Artist]:
        """根据名称获取艺术家及其歌曲"""
        from sqlalchemy.orm import selectinload
        stmt = select(Artist).options(selectinload(Artist.songs)).where(Artist.name == name)
        result = await self._session.execute(stmt)
        return result.scalars().first()
    
    async def get_with_details(self, artist_id: int) -> Optional[Artist]:
        """获取艺人详细信息及其来源、歌曲"""
        from sqlalchemy.orm import selectinload
        from app.models.song import Song
        stmt = (
            select(Artist)
            .options(
                selectinload(Artist.sources),
                selectinload(Artist.songs).selectinload(Song.sources)
            )
            .where(Artist.id == artist_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_by_name(self, name: str, source: str = "local", source_id: str = None) -> Artist:
        """
        根据名称获取或创建艺术家 (Logical Entity)
        If source is provided and it's 'local', we might not create Source record yet? 
        Refactored: This method focuses on Logical Entity.
        """
        artist = await self.get_by_name(name)
        if artist:
            return artist
        
        new_artist = Artist(
            name=name,
            status="active"
        )
        
        self._session.add(new_artist)
        await self._session.flush()
        await self._session.refresh(new_artist)
        
        # If specific source info provided (e.g. from ID3), should we add ArtistSource?
        if source and source != 'local' and source_id:
            from app.models.artist import ArtistSource
            s = ArtistSource(
                artist_id=new_artist.id, 
                source=source, 
                source_id=source_id
            )
            self._session.add(s)
            await self._session.flush()
            
        return new_artist

    async def get_song_count(self, artist_id: int) -> int:
        """获取歌手歌曲数量"""
        from app.models.song import Song
        from sqlalchemy import func
        stmt = select(func.count(Song.id)).where(Song.artist_id == artist_id)
        result = await self._session.execute(stmt)
        return result.scalar() or 0