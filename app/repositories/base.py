from typing import Any, Generic, Optional, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: Type[ModelT], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, id: int) -> Optional[ModelT]:
        return await self.db.get(self.model, id)

    async def list(self, limit: int = 50, offset: int = 0) -> tuple[list[ModelT], int]:
        total = await self.db.scalar(select(func.count()).select_from(self.model))
        result = await self.db.execute(select(self.model).limit(limit).offset(offset))
        return list(result.scalars().all()), total or 0

    async def create(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelT, data: dict[str, Any]) -> ModelT:
        for key, val in data.items():
            setattr(obj, key, val)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.db.delete(obj)
        await self.db.commit()
