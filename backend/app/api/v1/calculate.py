from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_uow, require_roles
from app.db.models import User
from app.domain.dto.calculation import (
    BatchPriceDTO,
    CalculateRequestDTO,
    CalculationResultDTO,
)
from app.domain.enums import UserRole
from app.repositories.uow import UnitOfWork
from app.services.calculation_service import CalculationDataError, CalculationService

router = APIRouter(prefix="/calculate", tags=["calculate"])


@router.post("/25d-feature")
async def calculate_25d_feature(
    payload: CalculateRequestDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[
        User,
        Depends(require_roles(UserRole.MANAGER, UserRole.TECHNOLOGIST, UserRole.ADMIN)),
    ],
) -> CalculationResultDTO:
    try:
        return await CalculationService(uow).calculate(payload)
    except CalculationDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post("/25d-feature/ladder")
async def calculate_batch_ladder(
    payload: CalculateRequestDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[
        User,
        Depends(require_roles(UserRole.MANAGER, UserRole.TECHNOLOGIST, UserRole.ADMIN)),
    ],
) -> list[BatchPriceDTO]:
    """Цены за деталь по тиражам 1/5/10/25/50/100 + текущая партия."""
    try:
        return await CalculationService(uow).ladder(payload)
    except CalculationDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
