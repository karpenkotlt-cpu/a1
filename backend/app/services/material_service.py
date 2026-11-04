from collections.abc import Sequence

from app.db.models import Material, MaterialMachinability
from app.domain.dto.material import MaterialCreate, MaterialRead, MaterialUpdate
from app.repositories.uow import UnitOfWork


class MaterialAlreadyExistsError(Exception):
    pass


def _to_read(material: Material) -> MaterialRead:
    dto = MaterialRead.model_validate(material)
    mach: MaterialMachinability
    for mach in material.machinability_overrides:
        if mach.operation_group == "ALL":
            dto.k_mach_finish = mach.k_finish_factor
            dto.tool_wear = mach.tool_wear_factor
            break
    return dto


class MaterialService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list_all(self) -> Sequence[MaterialRead]:
        materials = await self._uow.materials.list_all()
        return [_to_read(material) for material in materials]

    async def get(self, material_id: int) -> MaterialRead | None:
        material = await self._uow.materials.get_with_machinability(material_id)
        return None if material is None else _to_read(material)

    async def create(self, dto: MaterialCreate) -> MaterialRead:
        if await self._uow.materials.get_by_grade(dto.grade) is not None:
            raise MaterialAlreadyExistsError(dto.grade)
        material = Material(**dto.model_dump())
        self._uow.materials.add(material)
        await self._uow.commit()
        fetched = await self._uow.materials.get_with_machinability(material.id)
        assert fetched is not None
        return _to_read(fetched)

    async def update(
        self, material_id: int, dto: MaterialUpdate
    ) -> MaterialRead | None:
        material = await self._uow.materials.get(material_id)
        if material is None:
            return None
        data = dto.model_dump(exclude_unset=True)
        if "grade" in data and data["grade"] != material.grade:
            existing = await self._uow.materials.get_by_grade(str(data["grade"]))
            if existing is not None and existing.id != material.id:
                raise MaterialAlreadyExistsError(str(data["grade"]))
        for field, value in data.items():
            setattr(material, field, value)
        await self._uow.commit()
        fetched = await self._uow.materials.get_with_machinability(material_id)
        assert fetched is not None
        return _to_read(fetched)

    async def delete(self, material_id: int) -> bool:
        material = await self._uow.materials.get(material_id)
        if material is None:
            return False
        await self._uow.materials.delete(material)
        await self._uow.commit()
        return True
