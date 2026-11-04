from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.master_data import (
    AuxiliaryOperationRepository,
    CapacityLoadRepository,
    CoefficientRepository,
    CooperationServiceRepository,
    DrillingRateRepository,
    OperationRateRepository,
    OperationRepository,
    ToolBasketRepository,
    WorkCenterRepository,
)
from app.repositories.materials import MaterialRepository
from app.repositories.quotes import QuoteRepository
from app.repositories.users import UserRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.materials = MaterialRepository(session)
        self.operations = OperationRepository(session)
        self.operation_rates = OperationRateRepository(session)
        self.drilling_rates = DrillingRateRepository(session)
        self.coefficients = CoefficientRepository(session)
        self.cooperation_services = CooperationServiceRepository(session)
        self.capacity_loads = CapacityLoadRepository(session)
        self.work_centers = WorkCenterRepository(session)
        self.quotes = QuoteRepository(session)
        self.auxiliary_operations = AuxiliaryOperationRepository(session)
        self.tool_baskets = ToolBasketRepository(session)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            await self.session.rollback()

    async def commit(self) -> None:
        await self.session.commit()
