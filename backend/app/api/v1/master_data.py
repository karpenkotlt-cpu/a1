from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_uow, require_roles
from app.db.models import User
from app.domain.dto.master_data import (
    AuxiliaryOperationReadDTO,
    AuxiliaryOperationUpdateDTO,
    CapacityLoadCreateDTO,
    CapacityLoadReadDTO,
    CapacityLoadUpdateDTO,
    CoefficientReadDTO,
    CoefficientUpdateDTO,
    CooperationServiceCreateDTO,
    CooperationServiceReadDTO,
    CooperationServiceUpdateDTO,
    DrillingRateReadDTO,
    DrillingRateUpdateDTO,
    OperationRateReadDTO,
    OperationRateUpdateDTO,
    OperationReadDTO,
    OperationUpdateDTO,
    WorkCenterReadDTO,
    WorkCenterUpdateDTO,
)
from app.domain.enums import UserRole
from app.repositories.uow import UnitOfWork
from app.services.master_data_service import MasterDataService

router = APIRouter(tags=["master-data"])


@router.get("/operations")
async def list_operations(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[OperationReadDTO]:
    return list(await MasterDataService(uow).list_operations())


@router.patch("/operations/{operation_id}")
async def update_operation(
    operation_id: int,
    payload: OperationUpdateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> OperationReadDTO:
    operation = await MasterDataService(uow).update_operation(operation_id, payload)
    if operation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Операция не найдена",
        )
    return operation


@router.patch("/operation-rates/{rate_id}")
async def update_operation_rate(
    rate_id: int,
    payload: OperationRateUpdateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> OperationRateReadDTO:
    rate = await MasterDataService(uow).update_operation_rate(rate_id, payload)
    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ставка производительности не найдена",
        )
    return rate


@router.get("/work-centers")
async def list_work_centers(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[WorkCenterReadDTO]:
    return list(await MasterDataService(uow).list_work_centers())


@router.patch("/work-centers/{center_id}")
async def update_work_center(
    center_id: int,
    payload: WorkCenterUpdateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> WorkCenterReadDTO:
    center = await MasterDataService(uow).update_work_center(center_id, payload)
    if center is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рабочий центр не найден",
        )
    return center


@router.get("/coefficients")
async def list_coefficients(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[CoefficientReadDTO]:
    return list(await MasterDataService(uow).list_coefficients())


@router.patch("/coefficients/{coefficient_id}")
async def update_coefficient(
    coefficient_id: int,
    payload: CoefficientUpdateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> CoefficientReadDTO:
    coefficient = await MasterDataService(uow).update_coefficient(
        coefficient_id, payload
    )
    if coefficient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Коэффициент не найден",
        )
    return coefficient


@router.get("/auxiliary-operations")
async def list_auxiliary_operations(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[AuxiliaryOperationReadDTO]:
    return list(await MasterDataService(uow).list_auxiliary_operations())


@router.patch("/auxiliary-operations/{operation_id}")
async def update_auxiliary_operation(
    operation_id: int,
    payload: AuxiliaryOperationUpdateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> AuxiliaryOperationReadDTO:
    operation = await MasterDataService(uow).update_auxiliary_operation(
        operation_id, payload
    )
    if operation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вспомогательная операция не найдена",
        )
    return operation


@router.get("/drilling-rates")
async def list_drilling_rates(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[DrillingRateReadDTO]:
    return list(await MasterDataService(uow).list_drilling_rates())


@router.patch("/drilling-rates/{rate_id}")
async def update_drilling_rate(
    rate_id: int,
    payload: DrillingRateUpdateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> DrillingRateReadDTO:
    rate = await MasterDataService(uow).update_drilling_rate(rate_id, payload)
    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Диапазон сверления не найден",
        )
    return rate


@router.get("/cooperation-services")
async def list_cooperation_services(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[CooperationServiceReadDTO]:
    return list(await MasterDataService(uow).list_cooperation_services())


@router.post("/cooperation-services", status_code=status.HTTP_201_CREATED)
async def create_cooperation_service(
    payload: CooperationServiceCreateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> CooperationServiceReadDTO:
    return await MasterDataService(uow).create_cooperation_service(payload)


@router.patch("/cooperation-services/{service_id}")
async def update_cooperation_service(
    service_id: int,
    payload: CooperationServiceUpdateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> CooperationServiceReadDTO:
    service = await MasterDataService(uow).update_cooperation_service(
        service_id, payload
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Услуга кооперации не найдена",
        )
    return service


@router.delete(
    "/cooperation-services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_cooperation_service(
    service_id: int,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> None:
    deleted = await MasterDataService(uow).delete_cooperation_service(service_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Услуга кооперации не найдена",
        )


@router.get("/capacity")
async def list_capacity_loads(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[CapacityLoadReadDTO]:
    return list(await MasterDataService(uow).list_capacity_loads())


@router.post("/capacity", status_code=status.HTTP_201_CREATED)
async def create_capacity_load(
    payload: CapacityLoadCreateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> CapacityLoadReadDTO:
    row = await MasterDataService(uow).create_capacity_load(payload)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Группа уже заведена в APS-загрузке",
        )
    return row


@router.patch("/capacity/{load_id}")
async def update_capacity_load(
    load_id: int,
    payload: CapacityLoadUpdateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> CapacityLoadReadDTO:
    row = await MasterDataService(uow).update_capacity_load(load_id, payload)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Строка загрузки не найдена",
        )
    return row
