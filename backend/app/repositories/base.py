from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: int) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def list_all(self) -> Sequence[ModelT]:
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
