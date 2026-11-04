from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_uow, require_roles
from app.db.models import User
from app.domain.dto.material import MaterialCreate, MaterialRead, MaterialUpdate
from app.domain.enums import UserRole
from app.repositories.uow import UnitOfWork
from app.services.material_service import MaterialAlreadyExistsError, MaterialService

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("")
async def list_materials(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[MaterialRead]:
    return list(await MaterialService(uow).list_all())


@router.get("/{material_id}")
async def get_material(
    material_id: int,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> MaterialRead:
    material = await MaterialService(uow).get(material_id)
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Материал не найден"
        )
    return material


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_material(
    payload: MaterialCreate,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> MaterialRead:
    try:
        return await MaterialService(uow).create(payload)
    except MaterialAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Материал с такой маркой уже существует",
        ) from exc


@router.patch("/{material_id}")
async def update_material(
    material_id: int,
    payload: MaterialUpdate,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> MaterialRead:
    try:
        material = await MaterialService(uow).update(material_id, payload)
    except MaterialAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Материал с такой маркой уже существует",
        ) from exc
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Материал не найден"
        )
    return material


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: int,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> None:
    deleted = await MaterialService(uow).delete(material_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Материал не найден"
        )
