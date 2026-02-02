from typing import TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import delete, update

T = TypeVar('T', bound=DeclarativeBase)

class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]):
        self._session = session
        self._model = model

    async def get(self, id: int) -> Optional[T]:
        stmt = select(self._model).where(self._model.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        stmt = select(self._model)
        
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(self._model, key) == value)
        
        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj: T) -> T:
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def update(self, id: int, obj_data: Dict[str, Any]) -> Optional[T]:
        stmt = update(self._model).where(self._model.id == id).values(**obj_data)
        await self._session.execute(stmt)
        await self._session.commit()
        
        return await self.get(id)

    async def delete(self, id: int) -> bool:
        stmt = delete(self._model).where(self._model.id == id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0