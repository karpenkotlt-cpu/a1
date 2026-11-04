import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuxiliaryOperation,
    Coefficient,
    DrillingRate,
    MachineFinancialProfile,
    Material,
    MaterialMachinability,
    Operation,
    OperationPerformanceRate,
    ToolBasket,
    WorkCenter,
)
from app.db.models.enums import CoefficientType, MachineType, OperationType
from app.db.session import session_factory

BASE_ISO_GROUP = "P"

MATERIALS: list[tuple[str, str | None, str, str, str, str, str, str, str]] = [
    (
        "Сталь 45",
        "ГОСТ 1050-2013",
        "P",
        "7.82",
        "1.00",
        "1.00",
        "1.00",
        "120.50",
        "15.00",
    ),
    (
        "Ст3 / Сталь 20 / 09Г2С",
        "ГОСТ 535-2005",
        "P",
        "7.85",
        "1.15",
        "1.05",
        "0.85",
        "0.00",
        "0.00",
    ),
    (
        "40ХН2МА / 30ХГСА / 18ХГТ",
        "ГОСТ 4543-2016",
        "P",
        "7.85",
        "0.70",
        "0.80",
        "1.40",
        "0.00",
        "0.00",
    ),
    (
        "12Х18Н10Т / AISI 304 / 316",
        "ГОСТ 5632-2014",
        "M",
        "7.90",
        "0.55",
        "0.65",
        "1.80",
        "0.00",
        "0.00",
    ),
    (
        "20Х13 / 40Х13 / 14Х17Н2",
        "ГОСТ 5632-2014",
        "M",
        "7.76",
        "0.68",
        "0.75",
        "1.45",
        "0.00",
        "0.00",
    ),
    (
        "СЧ20 / СЧ25",
        "ГОСТ 1412-85",
        "K",
        "7.20",
        "1.25",
        "1.15",
        "0.90",
        "0.00",
        "0.00",
    ),
    (
        "ВЧ40 / ВЧ50",
        "ГОСТ 7293-85",
        "K",
        "7.15",
        "0.90",
        "0.95",
        "1.15",
        "0.00",
        "0.00",
    ),
    (
        "Д16Т / В95 / АМг6",
        "ГОСТ 4784-2019",
        "N",
        "2.78",
        "3.20",
        "2.50",
        "0.35",
        "0.00",
        "0.00",
    ),
    (
        "ЛС59-1 / Л63",
        "ГОСТ 15527-2004",
        "N",
        "8.50",
        "2.80",
        "2.40",
        "0.40",
        "0.00",
        "0.00",
    ),
    (
        "БрАЖ9-4 / БрОЦС5-5-5",
        "ГОСТ 18175-78",
        "N",
        "7.60",
        "1.40",
        "1.30",
        "0.90",
        "0.00",
        "0.00",
    ),
    (
        "Капролон / Фторопласт / ПОМ-С",
        None,
        "N",
        "1.15",
        "3.50",
        "2.00",
        "0.20",
        "0.00",
        "0.00",
    ),
    (
        "ВТ1-0 / ВТ6 / ВТ22",
        "ГОСТ 19807-91",
        "S",
        "4.43",
        "0.28",
        "0.38",
        "3.20",
        "0.00",
        "0.00",
    ),
    (
        "Х12МФ / ШХ15 (HRC 50-60)",
        "ГОСТ 5950-2000",
        "H",
        "7.80",
        "0.18",
        "0.35",
        "3.80",
        "0.00",
        "0.00",
    ),
]

OPERATIONS: list[tuple[str, str, str, str, str, str, str | None, str]] = [
    (
        "TURN_CNC_EXT",
        "Токарная ЧПУ: наружное точение",
        "TURNING",
        "TURNING_CNC",
        "48.00",
        "3.80",
        None,
        "40.0",
    ),
    (
        "TURN_CNC_INT",
        "Токарная ЧПУ: внутренняя расточка",
        "TURNING",
        "TURNING_CNC",
        "22.00",
        "2.20",
        "20.0",
        "45.0",
    ),
    (
        "TURN_MANUAL",
        "Токарная универсальная (16К20)",
        "TURNING",
        "TURNING_MANUAL",
        "18.00",
        "1.40",
        None,
        "25.0",
    ),
    (
        "MILL_CNC_FACE",
        "Фрезерная ЧПУ: торцевание и уступы (D50-63)",
        "MILLING",
        "MILLING_3AXIS",
        "38.00",
        "6.50",
        "50.0",
        "45.0",
    ),
    (
        "MILL_CNC_D16",
        "Фрезерная ЧПУ: карманы средние (D16-20)",
        "MILLING",
        "MILLING_3AXIS",
        "24.00",
        "2.60",
        "16.0",
        "45.0",
    ),
    (
        "MILL_CNC_D10",
        "Фрезерная ЧПУ: карманы малые (D8-12)",
        "MILLING",
        "MILLING_3AXIS",
        "9.50",
        "1.50",
        "8.0",
        "45.0",
    ),
    (
        "MILL_CNC_D5",
        "Фрезерная ЧПУ: узкие пазы и радиусы (D4-6)",
        "MILLING",
        "MILLING_3AXIS",
        "2.20",
        "0.65",
        "4.0",
        "50.0",
    ),
    (
        "MILL_CNC_D3",
        "Фрезерная ЧПУ: микро-фрезерование (D2-3)",
        "MILLING",
        "MILLING_3AXIS",
        "0.45",
        "0.22",
        "2.0",
        "60.0",
    ),
    (
        "MILL_5AXIS_3D",
        "5-осевая ЧПУ: 3D-поверхности",
        "MILLING",
        "MILLING_5AXIS",
        "14.00",
        "0.55",
        "10.0",
        "45.0",
    ),
    (
        "GRIND_CYL",
        "Кругло-/плоскошлифовальная",
        "GRINDING",
        "GRINDING",
        "1.80",
        "0.95",
        None,
        "40.0",
    ),
]

WORK_CENTERS: list[tuple[str, str, str, str, str | None]] = [
    ("TURN_CNC_01", "Токарный ЧПУ 16А20Ф3", "TURNING_CNC", "TURNING_CNC", "15.0"),
    (
        "TURN_MANUAL_01",
        "Токарный универсальный 16К20",
        "TURNING_CONVENTIONAL",
        "TURNING_MANUAL",
        None,
    ),
    (
        "MILL_3AX_01",
        "Вертикальный фрезерный ОЦ (BT40)",
        "MILLING_3AXIS",
        "MILLING_3AXIS",
        "10.0",
    ),
    ("MC_5AXIS_01", "5-осевой ОЦ DMG Mori", "MILLING_5AXIS", "MILLING_5AXIS", "14.0"),
    ("GRIND_01", "Круглошлифовальный 3М131", "GRINDING", "GRINDING", None),
    ("WEDM_01", "Проволочный электроэрозионный", "WEDM", "WEDM", None),
]

COEFFICIENTS: list[tuple[str, str, str, str | None]] = [
    ("TOLERANCE", "IT12-14", "0.65", "Ra6.3-12.5, свободные размеры"),
    ("TOLERANCE", "IT10-11", "1.00", "Ra3.2, базовый чистовой проход"),
    ("TOLERANCE", "IT8-9", "1.65", "Ra1.6, два чистовых прохода"),
    ("TOLERANCE", "IT7", "2.60", "Ra0.8-1.6, пробный проход + промер"),
    ("TOLERANCE", "IT6", "4.20", "Ra0.4-0.8, посадка под подшипник"),
    ("GEOMETRY", "THIN_WALL", "0.45", "twall<2.5мм или L/D>7: Q×0.45"),
    ("GEOMETRY", "INTERRUPTED_CUT", "0.65", "Прерывистое резание: Q×0.65, Kwear×1.70"),
]

DRILLING_RATES: list[tuple[str, str, str, str]] = [
    ("3.0", "5.5", "280", "75"),
    ("6.0", "10.5", "380", "95"),
    ("11.0", "16.0", "340", "80"),
    ("16.5", "26.0", "240", "55"),
    ("27.0", "45.0", "160", "35"),
]

AUXILIARY_OPERATIONS: list[tuple[str, str, str, str]] = [
    ("FITTING", "Слесарная (снятие заусенцев)", "3.00", "1.2000"),
    ("QC", "ОТК (контроль размеров)", "2.50", "1.2000"),
]

# (group, cost_rub, life_min, regrindable, d_from, d_to)
TOOL_BASKETS: list[tuple[str, str, str, bool, str | None, str | None]] = [
    ("TURN_CNC_EXT", "4500.00", "55", False, None, None),
    ("TURN_CNC_INT", "5200.00", "50", False, None, None),
    ("TURN_MANUAL", "1500.00", "60", False, None, None),
    ("MILL_CNC_FACE", "6000.00", "50", False, None, None),
    ("MILL_CNC_D16", "3800.00", "45", True, None, None),
    ("MILL_CNC_D10", "2200.00", "40", True, None, None),
    ("MILL_CNC_D5", "900.00", "35", True, None, None),
    ("MILL_CNC_D3", "350.00", "30", True, None, None),
    ("MILL_5AXIS_3D", "7000.00", "45", True, None, None),
    ("DRILL_CARBIDE", "1400.00", "40", True, "3.0", "5.5"),
    ("DRILL_CARBIDE", "2600.00", "45", True, "6.0", "10.5"),
    ("DRILL_CARBIDE", "4900.00", "50", True, "11.0", "16.0"),
    ("DRILL_CARBIDE", "11000.00", "55", True, "16.5", "26.0"),
    ("DRILL_CARBIDE", "26000.00", "60", True, "27.0", "45.0"),
    ("DRILL_HSS", "150.00", "20", False, "3.0", "5.5"),
    ("DRILL_HSS", "280.00", "25", False, "6.0", "10.5"),
    ("DRILL_HSS", "550.00", "25", False, "11.0", "16.0"),
    ("DRILL_HSS", "1200.00", "25", False, "16.5", "26.0"),
]

CENTER_PROFILES: dict[str, dict[str, str | int]] = {
    "MC_5AXIS_01": {
        "machine_cost": "25000000.00",
        "depreciation_years": 7,
        "energy_cost_per_hour": "112.00",
        "operator_rate_per_hour": "36.00",
        "multi_machine_factor": "2.00",
        "shop_overhead_percent": "65.00",
        "plant_overhead_percent": "30.00",
        "machine_rate_per_min": "47.9900",
    },
    "TURN_CNC_01": {
        "machine_rate_per_min": "30.0000",
    },
    "MILL_3AX_01": {
        "machine_rate_per_min": "20.0000",
    },
}


async def seed_materials(session: AsyncSession) -> int:
    count = 0
    for grade, gost, iso, density, kq, ks, kw, cost, scrap in MATERIALS:
        result = await session.execute(select(Material).where(Material.grade == grade))
        material = result.scalars().one_or_none()
        if material is None:
            material = Material(
                grade=grade,
                gost=gost,
                iso_group=iso,
                density_g_cm3=Decimal(density),
                machinability_factor=Decimal(kq),
                cost_per_kg=Decimal(cost),
                scrap_price_per_kg=Decimal(scrap),
            )
            session.add(material)
            await session.flush()
            count += 1
        else:
            material.density_g_cm3 = Decimal(density)
            material.machinability_factor = Decimal(kq)
        mach_result = await session.execute(
            select(MaterialMachinability).where(
                MaterialMachinability.material_id == material.id,
                MaterialMachinability.operation_group == "ALL",
            )
        )
        mach = mach_result.scalars().one_or_none()
        if mach is None:
            mach = MaterialMachinability(material_id=material.id)
            session.add(mach)
        mach.machinability_factor = Decimal(kq)
        mach.k_finish_factor = Decimal(ks)
        mach.tool_wear_factor = Decimal(kw)
    return count


async def seed_operations(session: AsyncSession) -> int:
    count = 0
    for code, name, op_type, wc_group, q, s, min_tool, setup in OPERATIONS:
        result = await session.execute(select(Operation).where(Operation.code == code))
        operation = result.scalars().one_or_none()
        if operation is None:
            operation = Operation(code=code)
            session.add(operation)
            count += 1
        operation.name = name
        operation.operation_type = OperationType(op_type)
        operation.work_center_group = wc_group
        operation.min_tool_diameter_mm = (
            Decimal(min_tool) if min_tool is not None else None
        )
        operation.setup_time_base_min = Decimal(setup)
        rate_result = await session.execute(
            select(OperationPerformanceRate).where(
                OperationPerformanceRate.operation_id == operation.id,
                OperationPerformanceRate.material_iso_group == BASE_ISO_GROUP,
            )
        )
        rate = rate_result.scalars().one_or_none()
        if rate is None:
            rate = OperationPerformanceRate(
                operation_id=operation.id,
                material_iso_group=BASE_ISO_GROUP,
                q_rough_cm3_min=Decimal(q),
                s_finish_dm2_min=Decimal(s),
            )
            session.add(rate)
        else:
            rate.q_rough_cm3_min = Decimal(q)
            rate.s_finish_dm2_min = Decimal(s)
    return count


async def seed_work_centers(session: AsyncSession) -> int:
    count = 0
    for code, name, machine_type, group_code, power in WORK_CENTERS:
        result = await session.execute(
            select(WorkCenter).where(WorkCenter.code == code)
        )
        center = result.scalars().one_or_none()
        if center is None:
            center = WorkCenter(code=code)
            session.add(center)
            count += 1
        center.name = name
        center.machine_type = MachineType(machine_type)
        center.group_code = group_code
        center.spindle_power_kw = Decimal(power) if power else None
    profile_result = await session.execute(select(WorkCenter))
    centers_by_code = {center.code: center for center in profile_result.scalars()}
    for code, fields in CENTER_PROFILES.items():
        center = centers_by_code[code]
        profile_select = await session.execute(
            select(MachineFinancialProfile).where(
                MachineFinancialProfile.work_center_id == center.id
            )
        )
        profile = profile_select.scalars().one_or_none()
        if profile is None:
            profile = MachineFinancialProfile(work_center_id=center.id)
            session.add(profile)
        for field, value in fields.items():
            setattr(
                profile,
                field,
                int(value) if field == "depreciation_years" else Decimal(value),
            )
    return count


async def seed_drilling(session: AsyncSession) -> int:
    existing = await session.execute(select(DrillingRate))
    rows = existing.scalars().all()
    if len(rows) == len(DRILLING_RATES):
        return 0
    for row in rows:
        await session.delete(row)
    session.add_all(
        DrillingRate(
            diameter_from_mm=Decimal(f),
            diameter_to_mm=Decimal(t),
            carbide_feed_mm_min=Decimal(c),
            hss_feed_mm_min=Decimal(h),
        )
        for f, t, c, h in DRILLING_RATES
    )
    return len(DRILLING_RATES)


async def seed_coefficients(session: AsyncSession) -> int:
    count = 0
    for coef_type, code, multiplier, description in COEFFICIENTS:
        result = await session.execute(
            select(Coefficient).where(
                Coefficient.coef_type == CoefficientType(coef_type),
                Coefficient.code == code,
            )
        )
        coefficient = result.scalars().one_or_none()
        if coefficient is None:
            coefficient = Coefficient(coef_type=CoefficientType(coef_type), code=code)
            session.add(coefficient)
            count += 1
        coefficient.multiplier = Decimal(multiplier)
        coefficient.description = description
    return count


async def seed_auxiliary(session: AsyncSession) -> int:
    count = 0
    for code, name, fixed, rate in AUXILIARY_OPERATIONS:
        result = await session.execute(
            select(AuxiliaryOperation).where(AuxiliaryOperation.code == code)
        )
        row = result.scalars().one_or_none()
        if row is None:
            row = AuxiliaryOperation(code=code)
            session.add(row)
            count += 1
        row.name = name
        row.fixed_time_min = Decimal(fixed)
        row.rate_per_min = Decimal(rate)
        row.is_active = True
    return count


async def seed_tool_baskets(session: AsyncSession) -> int:
    existing = await session.execute(select(ToolBasket))
    rows = existing.scalars().all()
    if len(rows) == len(TOOL_BASKETS):
        return 0
    for row in rows:
        await session.delete(row)
    await session.flush()
    session.add_all(
        ToolBasket(
            operation_group=group,
            material_iso_group="P",
            tool_set_cost=Decimal(cost),
            tool_life_min=Decimal(life),
            regrindable=regrindable,
            diameter_from_mm=Decimal(d_from) if d_from else None,
            diameter_to_mm=Decimal(d_to) if d_to else None,
        )
        for group, cost, life, regrindable, d_from, d_to in TOOL_BASKETS
    )
    return len(TOOL_BASKETS)


async def main() -> None:
    async with session_factory() as session:
        materials = await seed_materials(session)
        operations = await seed_operations(session)
        centers = await seed_work_centers(session)
        coefficients = await seed_coefficients(session)
        drilling = await seed_drilling(session)
        auxiliary = await seed_auxiliary(session)
        baskets = await seed_tool_baskets(session)
        await session.commit()
    print(
        f"Seed complete: +{materials} materials, +{operations} operations, "
        f"+{centers} work centers, +{coefficients} coefficients, "
        f"+{drilling} drilling bands, +{auxiliary} auxiliary ops, "
        f"+{baskets} tool baskets (updates applied idempotently)"
    )


if __name__ == "__main__":
    asyncio.run(main())
