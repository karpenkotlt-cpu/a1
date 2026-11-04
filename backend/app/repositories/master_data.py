from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import (
    AuxiliaryOperation,
    Coefficient,
    CooperationService,
    DrillingRate,
    MachineFinancialProfile,
    Operation,
    OperationPerformanceRate,
    ShopCapacityLoad,
    ToolBasket,
    WorkCenter,
)
from app.db.models.enums import CoefficientType
from app.repositories.base import Repository


class AuxiliaryOperationRepository(Repository[AuxiliaryOperation]):
    model = AuxiliaryOperation

    async def list_active(self) -> Sequence[AuxiliaryOperation]:
        result = await self.session.execute(
            select(AuxiliaryOperation)
            .where(AuxiliaryOperation.is_active.is_(True))
            .order_by(AuxiliaryOperation.id)
        )
        return result.scalars().all()

    async def list_all_ordered(self) -> Sequence[AuxiliaryOperation]:
        result = await self.session.execute(
            select(AuxiliaryOperation).order_by(AuxiliaryOperation.id)
        )
        return result.scalars().all()


class ToolBasketRepository(Repository[ToolBasket]):
    model = ToolBasket

    async def get_for_operation(self, operation_group: str) -> ToolBasket | None:
        result = await self.session.execute(
            select(ToolBasket).where(
                ToolBasket.operation_group == operation_group,
                ToolBasket.material_iso_group == "P",
            )
        )
        return result.scalars().one_or_none()

    async def list_drill_baskets(self) -> Sequence[ToolBasket]:
        result = await self.session.execute(
            select(ToolBasket)
            .where(
                ToolBasket.operation_group.like("DRILL_%"),
                ToolBasket.material_iso_group == "P",
            )
            .order_by(ToolBasket.id)
        )
        return result.scalars().all()


class OperationRepository(Repository[Operation]):
    model = Operation

    async def list_with_rates(self) -> Sequence[Operation]:
        result = await self.session.execute(
            select(Operation)
            .options(selectinload(Operation.performance_rates))
            .order_by(Operation.id)
        )
        return result.scalars().all()

    async def get_by_code(self, code: str) -> Operation | None:
        result = await self.session.execute(
            select(Operation).where(Operation.code == code)
        )
        return result.scalars().one_or_none()

    async def get_base_rate(self, operation_id: int) -> OperationPerformanceRate | None:
        result = await self.session.execute(
            select(OperationPerformanceRate).where(
                OperationPerformanceRate.operation_id == operation_id,
                OperationPerformanceRate.material_iso_group == "P",
            )
        )
        return result.scalars().one_or_none()


class OperationRateRepository(Repository[OperationPerformanceRate]):
    model = OperationPerformanceRate


class DrillingRateRepository(Repository[DrillingRate]):
    model = DrillingRate

    async def list_ordered(self) -> Sequence[DrillingRate]:
        result = await self.session.execute(
            select(DrillingRate).order_by(DrillingRate.diameter_from_mm)
        )
        return result.scalars().all()


class CoefficientRepository(Repository[Coefficient]):
    model = Coefficient

    async def get_multiplier(
        self, coef_type: CoefficientType, code: str
    ) -> float | None:
        result = await self.session.execute(
            select(Coefficient.multiplier).where(
                Coefficient.coef_type == coef_type,
                Coefficient.code == code,
            )
        )
        value = result.scalar_one_or_none()
        return None if value is None else float(value)


class CooperationServiceRepository(Repository[CooperationService]):
    model = CooperationService

    async def list_ordered(self) -> Sequence[CooperationService]:
        result = await self.session.execute(
            select(CooperationService).order_by(CooperationService.id)
        )
        return result.scalars().all()


class CapacityLoadRepository(Repository[ShopCapacityLoad]):
    model = ShopCapacityLoad

    async def list_ordered(self) -> Sequence[ShopCapacityLoad]:
        result = await self.session.execute(
            select(ShopCapacityLoad).order_by(ShopCapacityLoad.work_center_group)
        )
        return result.scalars().all()

    async def get_by_group(self, work_center_group: str) -> ShopCapacityLoad | None:
        result = await self.session.execute(
            select(ShopCapacityLoad).where(
                ShopCapacityLoad.work_center_group == work_center_group
            )
        )
        return result.scalars().one_or_none()


class WorkCenterRepository(Repository[WorkCenter]):
    model = WorkCenter

    async def list_with_profiles(self) -> Sequence[WorkCenter]:
        result = await self.session.execute(
            select(WorkCenter)
            .options(selectinload(WorkCenter.financial_profile))
            .order_by(WorkCenter.id)
        )
        return result.scalars().all()

    async def get_rate_for_group(self, group_code: str) -> Decimal | None:
        result = await self.session.execute(
            select(MachineFinancialProfile.machine_rate_per_min)
            .join(WorkCenter, WorkCenter.id == MachineFinancialProfile.work_center_id)
            .where(
                WorkCenter.group_code == group_code,
                WorkCenter.is_active.is_(True),
            )
            .order_by(MachineFinancialProfile.machine_rate_per_min)
            .limit(1)
        )
        return result.scalar_one_or_none()
