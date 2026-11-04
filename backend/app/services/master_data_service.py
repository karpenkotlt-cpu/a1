from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select

from app.db.models import (
    CooperationService,
    MachineFinancialProfile,
    Operation,
    ShopCapacityLoad,
    WorkCenter,
)
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
from app.repositories.uow import UnitOfWork


class MasterDataService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list_operations(self) -> Sequence[OperationReadDTO]:
        operations = await self._uow.operations.list_with_rates()
        return [self._operation_to_dto(op) for op in operations]

    async def update_operation(
        self, operation_id: int, dto: OperationUpdateDTO
    ) -> OperationReadDTO | None:
        operation = await self._uow.operations.get(operation_id)
        if operation is None:
            return None
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(operation, field, value)
        await self._uow.commit()
        # Повторный fetch с selectinload: rates не загружены после get(),
        # а ленивая загрузка в async-сессии невозможна.
        refreshed = await self._uow.operations.list_with_rates()
        target = next((op for op in refreshed if op.id == operation_id), None)
        return None if target is None else self._operation_to_dto(target)

    @staticmethod
    def _operation_to_dto(op: Operation) -> OperationReadDTO:
        # DTO строится явно: ORM-атрибут performance_rates != имени поля DTO,
        # from_attributes молча подставил бы default [].
        return OperationReadDTO(
            id=op.id,
            code=op.code,
            name=op.name,
            operation_type=op.operation_type.value,
            work_center_group=op.work_center_group,
            min_tool_diameter_mm=op.min_tool_diameter_mm,
            setup_time_base_min=op.setup_time_base_min,
            rates=[
                OperationRateReadDTO.model_validate(rate)
                for rate in op.performance_rates
            ],
        )

    async def update_operation_rate(
        self, rate_id: int, dto: OperationRateUpdateDTO
    ) -> OperationRateReadDTO | None:
        rate = await self._uow.operation_rates.get(rate_id)
        if rate is None:
            return None
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(rate, field, value)
        await self._uow.commit()
        await self._uow.session.refresh(rate)
        return OperationRateReadDTO.model_validate(rate)

    async def list_work_centers(self) -> Sequence[WorkCenterReadDTO]:
        centers = await self._uow.work_centers.list_with_profiles()
        return [self._center_to_dto(center) for center in centers]

    async def update_work_center(
        self, center_id: int, dto: WorkCenterUpdateDTO
    ) -> WorkCenterReadDTO | None:
        center = await self._uow.work_centers.get(center_id)
        if center is None:
            return None
        data = dto.model_dump(exclude_unset=True)
        rate = data.get("machine_rate_per_min")
        if rate is not None:
            await self._upsert_rate(center, rate)
        await self._uow.commit()
        refreshed = await self._uow.work_centers.list_with_profiles()
        target = next(c for c in refreshed if c.id == center_id)
        return self._center_to_dto(target)

    async def _upsert_rate(self, center: WorkCenter, machine_rate: Decimal) -> None:
        result = await self._uow.session.execute(
            select(MachineFinancialProfile).where(
                MachineFinancialProfile.work_center_id == center.id
            )
        )
        profile = result.scalars().one_or_none()
        if profile is None:
            profile = MachineFinancialProfile(
                work_center_id=center.id,
                machine_rate_per_min=machine_rate,
            )
            self._uow.session.add(profile)
        else:
            profile.machine_rate_per_min = machine_rate

    @staticmethod
    def _center_to_dto(center: WorkCenter) -> WorkCenterReadDTO:
        profile = center.financial_profile
        return WorkCenterReadDTO(
            id=center.id,
            code=center.code,
            name=center.name,
            machine_type=center.machine_type.value,
            group_code=center.group_code,
            is_active=center.is_active,
            machine_rate_per_min=(profile.machine_rate_per_min if profile else None),
            operator_rate_per_hour=(
                profile.operator_rate_per_hour if profile else None
            ),
        )

    async def list_coefficients(
        self,
    ) -> Sequence[CoefficientReadDTO]:
        coefficients = await self._uow.coefficients.list_all()
        return [CoefficientReadDTO.model_validate(coef) for coef in coefficients]

    async def update_coefficient(
        self, coefficient_id: int, dto: CoefficientUpdateDTO
    ) -> CoefficientReadDTO | None:
        coefficient = await self._uow.coefficients.get(coefficient_id)
        if coefficient is None:
            return None
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(coefficient, field, value)
        await self._uow.commit()
        await self._uow.session.refresh(coefficient)
        return CoefficientReadDTO.model_validate(coefficient)

    async def list_auxiliary_operations(
        self,
    ) -> Sequence[AuxiliaryOperationReadDTO]:
        operations = await self._uow.auxiliary_operations.list_all_ordered()
        return [AuxiliaryOperationReadDTO.model_validate(op) for op in operations]

    async def update_auxiliary_operation(
        self, operation_id: int, dto: AuxiliaryOperationUpdateDTO
    ) -> AuxiliaryOperationReadDTO | None:
        operation = await self._uow.auxiliary_operations.get(operation_id)
        if operation is None:
            return None
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(operation, field, value)
        await self._uow.commit()
        await self._uow.session.refresh(operation)
        return AuxiliaryOperationReadDTO.model_validate(operation)

    async def list_drilling_rates(self) -> Sequence[DrillingRateReadDTO]:
        rates = await self._uow.drilling_rates.list_ordered()
        return [DrillingRateReadDTO.model_validate(rate) for rate in rates]

    async def update_drilling_rate(
        self, rate_id: int, dto: DrillingRateUpdateDTO
    ) -> DrillingRateReadDTO | None:
        rate = await self._uow.drilling_rates.get(rate_id)
        if rate is None:
            return None
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(rate, field, value)
        await self._uow.commit()
        await self._uow.session.refresh(rate)
        return DrillingRateReadDTO.model_validate(rate)

    async def list_cooperation_services(
        self,
    ) -> Sequence[CooperationServiceReadDTO]:
        services = await self._uow.cooperation_services.list_ordered()
        return [CooperationServiceReadDTO.model_validate(s) for s in services]

    async def create_cooperation_service(
        self, dto: CooperationServiceCreateDTO
    ) -> CooperationServiceReadDTO:
        service = CooperationService(**dto.model_dump())
        self._uow.session.add(service)
        await self._uow.commit()
        await self._uow.session.refresh(service)
        return CooperationServiceReadDTO.model_validate(service)

    async def update_cooperation_service(
        self, service_id: int, dto: CooperationServiceUpdateDTO
    ) -> CooperationServiceReadDTO | None:
        service = await self._uow.cooperation_services.get(service_id)
        if service is None:
            return None
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(service, field, value)
        await self._uow.commit()
        await self._uow.session.refresh(service)
        return CooperationServiceReadDTO.model_validate(service)

    async def delete_cooperation_service(self, service_id: int) -> bool:
        service = await self._uow.cooperation_services.get(service_id)
        if service is None:
            return False
        await self._uow.cooperation_services.delete(service)
        await self._uow.commit()
        return True

    @staticmethod
    def _capacity_to_dto(row: ShopCapacityLoad) -> CapacityLoadReadDTO:
        # utilization считаем в Python: SQLite NUMERIC-affinity даёт
        # целочисленное деление в GENERATED-колонке (30% → 0); PG — корректен.
        utilization = (
            float(row.scheduled_minutes) / float(row.total_fund_minutes) * 100.0
            if row.total_fund_minutes not in (None, 0)
            else None
        )
        return CapacityLoadReadDTO(
            id=row.id,
            work_center_group=row.work_center_group,
            horizon_days=row.horizon_days,
            total_fund_minutes=row.total_fund_minutes,
            scheduled_minutes=row.scheduled_minutes,
            utilization_percent=utilization,
        )

    async def _capacity_refreshed(self, row_id: int) -> CapacityLoadReadDTO | None:
        rows = await self._uow.capacity_loads.list_ordered()
        target = next((row for row in rows if row.id == row_id), None)
        return None if target is None else self._capacity_to_dto(target)

    async def list_capacity_loads(self) -> Sequence[CapacityLoadReadDTO]:
        rows = await self._uow.capacity_loads.list_ordered()
        return [self._capacity_to_dto(row) for row in rows]

    async def create_capacity_load(
        self, dto: CapacityLoadCreateDTO
    ) -> CapacityLoadReadDTO | None:
        existing = await self._uow.capacity_loads.get_by_group(dto.work_center_group)
        if existing is not None:
            return None  # 409: группа уже заведена
        row = ShopCapacityLoad(**dto.model_dump())
        self._uow.session.add(row)
        await self._uow.commit()
        refreshed = await self._capacity_refreshed(row.id)
        assert refreshed is not None
        return refreshed

    async def update_capacity_load(
        self, row_id: int, dto: CapacityLoadUpdateDTO
    ) -> CapacityLoadReadDTO | None:
        row = await self._uow.capacity_loads.get(row_id)
        if row is None:
            return None
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await self._uow.commit()
        return await self._capacity_refreshed(row_id)
