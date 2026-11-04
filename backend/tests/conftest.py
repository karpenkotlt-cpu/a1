import asyncio
from collections.abc import AsyncIterator, Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.models import (
    AuxiliaryOperation,
    Base,
    Coefficient,
    CooperationService,
    DrillingRate,
    MachineFinancialProfile,
    Operation,
    OperationPerformanceRate,
    ShopCapacityLoad,
    ToolBasket,
    User,
    WorkCenter,
)
from app.db.models.enums import (
    CoefficientType,
    CooperationServiceType,
    MachineType,
    OperationType,
    PriceUnit,
)
from app.db.session import get_session
from app.domain.enums import UserRole
from app.main import app as fastapi_app

ADMIN_EMAIL = "admin@example.com"
MANAGER_EMAIL = "manager@example.com"
PASSWORD = "password123"

DRILLING_BANDS = [
    ("3.0", "5.5", "280", "75"),
    ("6.0", "10.5", "380", "95"),
    ("11.0", "16.0", "340", "80"),
    ("16.5", "26.0", "240", "55"),
    ("27.0", "45.0", "160", "35"),
]


def _master_data() -> list[object]:
    turning = Operation(
        code="TURN_CNC_EXT",
        name="Токарная ЧПУ: наружное точение",
        operation_type=OperationType.TURNING,
        work_center_group="TURNING_CNC",
        setup_time_base_min=Decimal("40.0"),
        performance_rates=[
            OperationPerformanceRate(
                material_iso_group="P",
                q_rough_cm3_min=Decimal("48.000"),
                s_finish_dm2_min=Decimal("3.800"),
            )
        ],
    )
    turning_int = Operation(
        code="TURN_CNC_INT",
        name="Токарная ЧПУ: внутренняя расточка",
        operation_type=OperationType.TURNING,
        work_center_group="TURNING_INT",
        setup_time_base_min=Decimal("45.0"),
        performance_rates=[
            OperationPerformanceRate(
                material_iso_group="P",
                q_rough_cm3_min=Decimal("22.000"),
                s_finish_dm2_min=Decimal("2.200"),
            )
        ],
    )
    milling = Operation(
        code="MILL_CNC_FACE",
        name="Фрезерная ЧПУ: торцевание",
        operation_type=OperationType.MILLING,
        work_center_group="MILLING_3AXIS",
        setup_time_base_min=Decimal("45.0"),
        performance_rates=[
            OperationPerformanceRate(
                material_iso_group="P",
                q_rough_cm3_min=Decimal("38.000"),
                s_finish_dm2_min=Decimal("6.500"),
            )
        ],
    )
    center = WorkCenter(
        code="TURN_CNC_01",
        name="Токарный ЧПУ 16А20Ф3",
        machine_type=MachineType.TURNING_CNC,
        group_code="TURNING_CNC",
        financial_profile=MachineFinancialProfile(
            machine_rate_per_min=Decimal("30.0000")
        ),
    )
    # Расточка — отдельная ячейка: маршрут T2 имеет две группы станков
    # (покрытие узкого места APS = max(Ugroup)). Ставка та же, чтобы
    # не менять золотые числа остальных тестов.
    turning_int_center = WorkCenter(
        code="TURN_INT_01",
        name="Токарный ЧПУ: расточной центр",
        machine_type=MachineType.TURNING_CNC,
        group_code="TURNING_INT",
        financial_profile=MachineFinancialProfile(
            machine_rate_per_min=Decimal("30.0000")
        ),
    )
    mill_center = WorkCenter(
        code="MILL_3AX_01",
        name="Вертикальный фрезерный ОЦ (BT40)",
        machine_type=MachineType.MILLING_3AXIS,
        group_code="MILLING_3AXIS",
        financial_profile=MachineFinancialProfile(
            machine_rate_per_min=Decimal("20.0000")
        ),
    )
    coefficients = [
        Coefficient(
            coef_type=CoefficientType.TOLERANCE,
            code="IT11",
            multiplier=Decimal("1.000"),
        ),
        Coefficient(
            coef_type=CoefficientType.TOLERANCE,
            code="IT7",
            multiplier=Decimal("2.600"),
        ),
    ]
    drilling = [
        DrillingRate(
            diameter_from_mm=Decimal(f),
            diameter_to_mm=Decimal(t),
            carbide_feed_mm_min=Decimal(c),
            hss_feed_mm_min=Decimal(h),
        )
        for f, t, c, h in DRILLING_BANDS
    ]
    auxiliary = [
        AuxiliaryOperation(
            code="FITTING",
            name="Слесарная (снятие заусенцев)",
            fixed_time_min=Decimal("3.00"),
            rate_per_min=Decimal("1.2000"),
        ),
        AuxiliaryOperation(
            code="QC",
            name="ОТК (контроль размеров)",
            fixed_time_min=Decimal("2.50"),
            rate_per_min=Decimal("1.2000"),
        ),
    ]
    tool_baskets = [
        ToolBasket(
            operation_group="TURN_CNC_EXT",
            material_iso_group="P",
            tool_set_cost=Decimal("4500.00"),
            tool_life_min=Decimal("55"),
            regrindable=False,
        ),
        ToolBasket(
            operation_group="DRILL_CARBIDE",
            material_iso_group="P",
            tool_set_cost=Decimal("4900.00"),
            tool_life_min=Decimal("50"),
            regrindable=True,
            diameter_from_mm=Decimal("11.0"),
            diameter_to_mm=Decimal("16.0"),
        ),
    ]
    cooperation = [
        CooperationService(
            service_type=CooperationServiceType.HEAT_TREATMENT,
            unit=PriceUnit.KG,
            price_per_unit=Decimal("85.00"),
            contractor="Термо-Пром",
            min_lot_qty=Decimal("20.00"),
        ),
        CooperationService(
            service_type=CooperationServiceType.GALVANIZING,
            unit=PriceUnit.DM2,
            price_per_unit=Decimal("40.00"),
        ),
    ]
    capacity = ShopCapacityLoad(
        work_center_group="TURNING_CNC",
        horizon_days=30,
        total_fund_minutes=Decimal("100000.00"),
        scheduled_minutes=Decimal("30000.00"),  # загрузка 30% → Kmargin 0.55
    )
    return [
        turning,
        turning_int,
        milling,
        center,
        turning_int_center,
        mill_center,
        *coefficients,
        *drilling,
        *auxiliary,
        *tool_baskets,
        *cooperation,
        capacity,
    ]


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async def prepare() -> async_sessionmaker[AsyncSession]:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            session.add_all(
                [
                    User(
                        email=ADMIN_EMAIL,
                        full_name="Admin",
                        password_hash=hash_password(PASSWORD),
                        role=UserRole.ADMIN,
                    ),
                    User(
                        email=MANAGER_EMAIL,
                        full_name="Manager",
                        password_hash=hash_password(PASSWORD),
                        role=UserRole.MANAGER,
                    ),
                    *(_master_data()),
                ]
            )
            await session.commit()
        return factory

    factory = asyncio.run(prepare())

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = override_get_session
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
