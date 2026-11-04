import math
from decimal import Decimal

import pytest

from app.domain.dto.calculation import (
    CalculateRequestDTO,
    HoleArrayFeature,
    MaterialInputDTO,
    StepDTO,
    T2Dimensions,
    T2Template,
    T5Dimensions,
    T5Template,
)
from app.domain.engine.costing import (
    AuxiliaryRate,
    DrillingBand,
    FeatureCostingEngine,
    MasterDataRates,
    OperationRates,
    ToolBasketRate,
)

BANDS = (
    DrillingBand(3.0, 5.5, 280.0),
    DrillingBand(6.0, 10.5, 380.0),
    DrillingBand(11.0, 16.0, 340.0),
    DrillingBand(16.5, 26.0, 240.0),
    DrillingBand(27.0, 45.0, 160.0),
)


def _request(margin: str = "0.00") -> CalculateRequestDTO:
    return CalculateRequestDTO(
        project_id="123e4567-e89b-12d3-a456-426614174000",
        batch_size=20,
        material=MaterialInputDTO(
            iso_group="P",
            k_mach_rough=Decimal("1.00"),
            k_mach_finish=Decimal("1.00"),
            density_g_cm3=Decimal("7.85"),
            cost_per_kg=Decimal("120.50"),
            scrap_price_per_kg=Decimal("15.00"),
        ),
        base_template=T2Template(
            type="T2_BUSHING",
            dimensions=T2Dimensions(
                outer_steps=[
                    StepDTO(diameter=160.0, length=20.0),
                    StepDTO(diameter=100.0, length=60.0),
                ],
                inner_steps=[
                    StepDTO(diameter=72.0, length=35.0),
                    StepDTO(diameter=60.0, length=45.0),
                ],
            ),
        ),
        features=[
            HoleArrayFeature(
                type="HOLE_ARRAY",
                count=6,
                diameter=11.0,
                depth=20.0,
                is_through=True,
            ),
            HoleArrayFeature(
                type="HOLE_ARRAY",
                count=4,
                diameter=6.0,
                depth=15.0,
                thread="M6",
            ),
        ],
        margin_percent=Decimal(margin),
    )


def _rates() -> MasterDataRates:
    return MasterDataRates(
        main=OperationRates(
            code="TURN_CNC_EXT",
            name="Токарная ЧПУ: наружное точение",
            q_rough_cm3_min=48.0,
            s_finish_dm2_min=3.8,
            setup_time_min=40.0,
            machine_rate_per_min=Decimal("30.0000"),
        ),
        inner=OperationRates(
            code="TURN_CNC_INT",
            name="Токарная ЧПУ: внутренняя расточка",
            q_rough_cm3_min=22.0,
            s_finish_dm2_min=2.2,
            setup_time_min=45.0,
            machine_rate_per_min=Decimal("30.0000"),
        ),
        kit_multiplier=1.0,
        drilling_bands=BANDS,
    )


V_OUTER = math.pi / 4 * (160**2 * 20 + 100**2 * 60)
V_INNER = math.pi / 4 * (72**2 * 35 + 60**2 * 45)
V_HOLES = 6 * math.pi / 4 * 11**2 * 20 + 4 * math.pi / 4 * 6**2 * 15
V_NET = V_OUTER - V_INNER - V_HOLES
V_GROSS = math.pi / 4 * 165.0**2 * 88.0
V_REMOVED = V_GROSS - V_NET
A_OUTER_DM2 = (
    math.pi * (160 * 20 + 100 * 60) + math.pi / 4 * (160**2 + 100**2)
) / 10000.0
A_INNER_DM2 = math.pi * (72 * 35 + 60 * 45) / 10000.0
T_ROUGH = V_REMOVED / 1000 / 48.0
T_DRILL = 6 * 22.0 / 340.0 + 4 * 17.0 / 380.0
MAIN_TIME = (T_ROUGH + A_OUTER_DM2 / 3.8 + T_DRILL) * 1.08
INNER_TIME = (A_INNER_DM2 / 2.2) * 1.08
MACHINE_TIME = MAIN_TIME + INNER_TIME
M_NET = V_NET * 7.85 / 1_000_000
M_GROSS = V_GROSS * 7.85 / 1_000_000
MATERIAL_COST = M_GROSS * 120.50 - (M_GROSS - M_NET) * 0.7 * 15.0
MACHINE_COST = MACHINE_TIME * 30.0 + (40.0 + 45.0) / 20 * 30.0
PRICE = MATERIAL_COST + MACHINE_COST
FLOOR_MACHINE = (T_ROUGH + A_OUTER_DM2 / 3.8 + T_DRILL) * 30.0 + (
    A_INNER_DM2 / 2.2
) * 30.0
FLOOR = MATERIAL_COST + FLOOR_MACHINE


def test_t2_geometry_volumes() -> None:
    result = FeatureCostingEngine.calculate(_request(), _rates())
    assert result.v_net_cm3 == pytest.approx(V_NET / 1000, abs=0.01)
    assert result.v_gross_cm3 == pytest.approx(V_GROSS / 1000, abs=0.01)
    assert result.v_removed_cm3 == pytest.approx(V_REMOVED / 1000, abs=0.02)


def test_t2_masses() -> None:
    result = FeatureCostingEngine.calculate(_request(), _rates())
    assert result.m_net_kg == pytest.approx(M_NET, abs=0.01)
    assert result.m_gross_kg == pytest.approx(M_GROSS, abs=0.01)


def test_t2_machine_time() -> None:
    result = FeatureCostingEngine.calculate(_request(), _rates())
    assert result.machine_time_min == pytest.approx(MACHINE_TIME, abs=0.02)
    assert result.setup_time_min == 85.0
    assert len(result.operations) == 2
    assert result.operations[0].machine_time_min == pytest.approx(MAIN_TIME, abs=0.02)
    assert result.operations[1].machine_time_min == pytest.approx(INNER_TIME, abs=0.02)
    assert result.operations[1].code == "TURN_CNC_INT"


def test_t2_price_without_margin() -> None:
    result = FeatureCostingEngine.calculate(_request(), _rates())
    assert float(result.material_cost) == pytest.approx(MATERIAL_COST, abs=0.02)
    assert float(result.price_per_part) == pytest.approx(PRICE, abs=0.02)
    assert float(result.batch_total_price) == pytest.approx(PRICE * 20, abs=0.1)


def test_t2_floor_price_variable_costs() -> None:
    """Пол цены = переменные издержки: основное время без α и Tпз,
    материал, кооперация, труд, инструмент. Не зависит от партии и всегда
    ниже полной цены (в полной цене есть α, Tпз/N и маржа)."""
    result = FeatureCostingEngine.calculate(_request(), _rates())
    assert result.floor_price_per_part is not None
    assert float(result.floor_price_per_part) == pytest.approx(FLOOR, abs=0.02)

    single = FeatureCostingEngine.calculate(
        _request().model_copy(update={"batch_size": 1}), _rates()
    )
    assert single.floor_price_per_part == result.floor_price_per_part
    assert float(result.floor_price_per_part) < float(result.price_per_part)

    priced = FeatureCostingEngine.calculate(
        _request().model_copy(update={"margin_percent": Decimal("35.00")}),
        _rates(),
    )
    assert float(priced.floor_price_per_part) < float(priced.price_per_part)


def test_t2_price_with_margin() -> None:
    result = FeatureCostingEngine.calculate(_request(margin="35.00"), _rates())
    assert float(result.price_per_part) == pytest.approx(PRICE * 1.35, abs=0.02)


def _t5_request(counterbore: bool = False) -> CalculateRequestDTO:
    return CalculateRequestDTO(
        project_id="123e4567-e89b-12d3-a456-426614174000",
        batch_size=10,
        material=MaterialInputDTO(
            iso_group="P",
            k_mach_rough=Decimal("1.00"),
            k_mach_finish=Decimal("1.00"),
            density_g_cm3=Decimal("7.85"),
            cost_per_kg=Decimal("120.50"),
            scrap_price_per_kg=Decimal("15.00"),
        ),
        base_template=T5Template(
            type="T5_HOUSING",
            dimensions=T5Dimensions(
                length=200.0,
                width=100.0,
                height=60.0,
                removal_ratio=0.6,
            ),
        ),
        features=[
            HoleArrayFeature(
                type="HOLE_ARRAY",
                count=4,
                diameter=11.0,
                depth=20.0,
                counterbore_diameter=18.0 if counterbore else None,
                counterbore_depth=5.0 if counterbore else None,
            )
        ],
        margin_percent=Decimal("0.00"),
    )


def _milling_rates() -> MasterDataRates:
    return MasterDataRates(
        main=OperationRates(
            code="MILL_CNC_FACE",
            name="Фрезерная ЧПУ: торцевание",
            q_rough_cm3_min=38.0,
            s_finish_dm2_min=6.5,
            setup_time_min=45.0,
            machine_rate_per_min=Decimal("20.0000"),
        ),
        kit_multiplier=1.0,
        drilling_bands=BANDS,
    )


T5_V_BASE = 200 * 100 * 60 * 0.4
T5_V_HOLES = 4 * math.pi / 4 * 11**2 * 20
T5_CB_EXTRA = 4 * math.pi / 4 * (18**2 - 11**2) * 5
T5_V_GROSS = 204.0 * 104.0 * 64.0
T5_A_SURF_DM2 = 2 * (200 * 100 + 200 * 60 + 100 * 60) / 10000
T5_MACHINE_TIME = (
    (T5_V_GROSS - (T5_V_BASE - T5_V_HOLES)) / 1000 / 38.0
    + T5_A_SURF_DM2 / 6.5
    + 4 * 22.0 / 340.0
) * 1.08


def test_t5_geometry_and_time() -> None:
    result = FeatureCostingEngine.calculate(_t5_request(), _milling_rates())
    assert result.v_net_cm3 == pytest.approx((T5_V_BASE - T5_V_HOLES) / 1000, abs=0.01)
    assert result.v_gross_cm3 == pytest.approx(T5_V_GROSS / 1000, abs=0.01)
    assert result.machine_time_min == pytest.approx(T5_MACHINE_TIME, abs=0.02)
    assert result.setup_time_min == 45.0
    assert len(result.operations) == 1
    assert result.operations[0].code == "MILL_CNC_FACE"


def test_counterbore_adds_volume() -> None:
    plain = FeatureCostingEngine.calculate(_t5_request(), _milling_rates())
    cored = FeatureCostingEngine.calculate(
        _t5_request(counterbore=True), _milling_rates()
    )
    assert plain.v_net_cm3 - cored.v_net_cm3 == pytest.approx(
        T5_CB_EXTRA / 1000, abs=0.01
    )


def test_auxiliary_operations_added() -> None:
    aux = (
        AuxiliaryRate("FITTING", "Слесарная", 3.0, Decimal("1.2000")),
        AuxiliaryRate("QC", "ОТК", 2.5, Decimal("1.2000")),
    )
    base = _rates()
    with_aux = MasterDataRates(
        main=base.main,
        inner=base.inner,
        kit_multiplier=base.kit_multiplier,
        drilling_bands=base.drilling_bands,
        auxiliary=aux,
    )
    plain = FeatureCostingEngine.calculate(_request(), base)
    extended = FeatureCostingEngine.calculate(_request(), with_aux)

    aux_cost = 3.0 * 1.2 + 2.5 * 1.2
    assert float(extended.price_per_part) == pytest.approx(
        float(plain.price_per_part) + aux_cost, abs=0.02
    )
    assert len(extended.operations) == 4
    assert {op.code for op in extended.operations} == {
        "TURN_CNC_EXT",
        "TURN_CNC_INT",
        "FITTING",
        "QC",
    }
    fitting = next(op for op in extended.operations if op.code == "FITTING")
    assert fitting.machine_time_min == 3.0
    assert fitting.cost == Decimal("3.60")


def test_tool_cost_model() -> None:
    base = _rates()
    bands = (
        DrillingBand(11.0, 16.0, 340.0, 80.0),
        DrillingBand(6.0, 10.5, 380.0, 95.0),
    )
    rates = MasterDataRates(
        main=base.main,
        inner=base.inner,
        kit_multiplier=base.kit_multiplier,
        drilling_bands=bands,
        main_basket=ToolBasketRate("TURN_CNC_EXT", Decimal("4500.00"), 55.0, False),
        inner_basket=ToolBasketRate("TURN_CNC_INT", Decimal("5200.00"), 50.0, False),
        drill_baskets=(
            ToolBasketRate("DRILL_CARBIDE", Decimal("4900.00"), 50.0, True, 11.0, 16.0),
            ToolBasketRate("DRILL_HSS", Decimal("280.00"), 25.0, False, 6.0, 10.5),
        ),
    )
    request = _request()
    request.features[1].drill_type = "HSS"
    plain_request = _request()
    plain_request.features[1].drill_type = "HSS"

    plain_rates = MasterDataRates(
        main=base.main,
        inner=base.inner,
        kit_multiplier=base.kit_multiplier,
        drilling_bands=bands,
    )
    plain = FeatureCostingEngine.calculate(plain_request, plain_rates)
    result = FeatureCostingEngine.calculate(request, rates)

    tool_main = (T_ROUGH + A_OUTER_DM2 / 3.8) * (4500.0 / 55.0) * 1.05
    tool_inner = (A_INNER_DM2 / 2.2) * (5200.0 / 50.0) * 1.05
    t_carb = 6 * 22.0 / 340.0
    tool_carb = t_carb * (4900.0 * 2.2 / (50.0 * 3)) * 1.05
    t_hss = 4 * 17.0 / 95.0
    tool_hss = t_hss * (280.0 / 25.0) * 1.05
    expected = tool_main + tool_inner + tool_carb + tool_hss

    assert float(result.tool_cost) == pytest.approx(expected, abs=0.03)
    assert float(result.price_per_part) == pytest.approx(
        float(plain.price_per_part) + expected, abs=0.03
    )
    main_op = next(op for op in result.operations if op.code == "TURN_CNC_EXT")
    assert float(main_op.tool_cost) == pytest.approx(
        tool_main + tool_carb + tool_hss, abs=0.03
    )
    inner_op = next(op for op in result.operations if op.code == "TURN_CNC_INT")
    assert float(inner_op.tool_cost) == pytest.approx(tool_inner, abs=0.03)


def test_special_tool_cost_charged_to_batch() -> None:
    base = _rates()
    request = _request()
    request.special_tool_cost = Decimal("10000.00")
    plain = FeatureCostingEngine.calculate(_request(), base)
    result = FeatureCostingEngine.calculate(request, base)
    assert float(result.price_per_part) == pytest.approx(
        float(plain.price_per_part) + 10000.0 / 20, abs=0.02
    )
