from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Material
from app.repositories.base import Repository


class MaterialRepository(Repository[Material]):
    model = Material

    async def list_all(self) -> Sequence[Material]:
        result = await self.session.execute(
            select(Material).options(selectinload(Material.machinability_overrides))
        )
        return result.scalars().all()

    async def get_with_machinability(self, material_id: int) -> Material | None:
        result = await self.session.execute(
            select(Material)
            .options(selectinload(Material.machinability_overrides))
            .where(Material.id == material_id)
        )
        return result.scalars().one_or_none()

    async def get_by_grade(self, grade: str) -> Material | None:
        result = await self.session.execute(
            select(Material).where(Material.grade == grade)
        )
        return result.scalars().one_or_none()
