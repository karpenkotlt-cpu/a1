from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_uow, require_roles
from app.db.models import User
from app.domain.dto.tool_basket import (
    ToolBasketReadDTO,
    ToolBasketUpdateDTO,
)
from app.domain.enums import UserRole
from app.repositories.uow import UnitOfWork
from app.services.tool_basket_service import ToolBasketService

router = APIRouter(prefix="/tool-baskets", tags=["tool-baskets"])


@router.get("")
async def list_tool_baskets(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ToolBasketReadDTO]:
    return list(await ToolBasketService(uow).list_all())


@router.patch("/{basket_id}")
async def update_tool_basket(
    basket_id: int,
    payload: ToolBasketUpdateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> ToolBasketReadDTO:
    basket = await ToolBasketService(uow).update(basket_id, payload)
    if basket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Корзина не найдена",
        )
    return basket
