from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.dto.calculation import (
    CalculateRequestDTO,
    CalculationResultDTO,
    CooperationBreakdownDTO,
    HoleArrayFeature,
    OperationBreakdownDTO,
)
from app.domain.engine import geometry

MONEY_QUANT = Decimal("0.01")
REGRIND_FACTOR = 0.6
REGRIND_COUNT = 2
TOOL_SCRAP_FACTOR = 1.05


@dataclass(frozen=True)
class DrillingBand:
    diameter_from_mm: float
    diameter_to_mm: float
    carbide_feed_mm_min: float
    hss_feed_mm_min: float = 0.0


@dataclass(frozen=True)
class ToolBasketRate:
    operation_group: str
    tool_set_cost: Decimal
    tool_life_min: float
    regrindable: bool = False
    diameter_from_mm: float | None = None
    diameter_to_mm: float | None = None


@dataclass(frozen=True)
class OperationRates:
    code: str
    name: str
    q_rough_cm3_min: float
    s_finish_dm2_min: float
    setup_time_min: float
    machine_rate_per_min: Decimal
    work_center_group: str = ""


@dataclass(frozen=True)
class AuxiliaryRate:
    code: str
    name: str
    fixed_time_min: float
    rate_per_min: Decimal


@dataclass(frozen=True)
class CooperationRate:
    """Услуга кооперации, разрешённая Services из справочника (без БД)."""

    service_id: int
    name: str
    unit: str  # KG | DM2 | METER | PIECE
    price_per_unit: Decimal
    min_lot_qty: Decimal = Decimal("0")


@dataclass(frozen=True)
class MasterDataRates:
    main: OperationRates
    inner: OperationRates | None = None
    kit_multiplier: float = 1.0
    drilling_bands: tuple[DrillingBand, ...] = ()
    auxiliary: tuple[AuxiliaryRate, ...] = ()
    main_basket: ToolBasketRate | None = None
    inner_basket: ToolBasketRate | None = None
    drill_baskets: tuple[ToolBasketRate, ...] = ()
    cooperation: tuple[CooperationRate, ...] = ()
    # Динамическая маржа APS: margin_eff = margin_percent × margin_multiplier
    margin_multiplier: float = 1.0
    capacity_utilization_percent: float | None = None
    bottleneck_group: str | None = None


def _carbide_feed(diameter: float, bands: tuple[DrillingBand, ...]) -> float | None:
    for band in bands:
        if band.diameter_from_mm <= diameter <= band.diameter_to_mm:
            return band.carbide_feed_mm_min
    return None


def _drill_feed(
    feature: HoleArrayFeature, bands: tuple[DrillingBand, ...]
) -> float | None:
    for band in bands:
        if band.diameter_from_mm <= feature.diameter <= band.diameter_to_mm:
            return (
                band.carbide_feed_mm_min
                if feature.drill_type == "CARBIDE"
                else band.hss_feed_mm_min
            )
    return None


def _basket_minute_cost(basket: ToolBasketRate) -> float:
    """₽/мин резания с учётом переточек монолитного ТС (K_regrind=0.6, 2 цикла)."""
    if basket.regrindable:
        life_multiplier = 1.0 + REGRIND_COUNT
        cost_multiplier = 1.0 + REGRIND_FACTOR * REGRIND_COUNT
        return (
            float(basket.tool_set_cost)
            * cost_multiplier
            / (basket.tool_life_min * life_multiplier)
        )
    return float(basket.tool_set_cost) / basket.tool_life_min


def _drill_basket_for(
    feature: HoleArrayFeature,
    baskets: tuple[ToolBasketRate, ...],
) -> ToolBasketRate | None:
    prefix = "DRILL_CARBIDE" if feature.drill_type == "CARBIDE" else "DRILL_HSS"
    for basket in baskets:
        if basket.operation_group != prefix:
            continue
        if (
            basket.diameter_from_mm is not None
            and basket.diameter_to_mm is not None
            and basket.diameter_from_mm <= feature.diameter <= basket.diameter_to_mm
        ):
            return basket
    return None


def _cooperation_qty(
    unit: str,
    m_net_kg: float,
    area_dm2: float,
    override: Decimal | None,
) -> Decimal:
    """Количество услуги на деталь: KG — по массе, DM2 — по площади,
    PIECE — штука, METER — только явное количество (длину реза 2.5D-модель
    не знает)."""
    if override is not None:
        return override
    if unit == "KG":
        return Decimal(str(round(m_net_kg, 3)))
    if unit == "DM2":
        return Decimal(str(round(area_dm2, 3)))
    if unit == "PIECE":
        return Decimal("1")
    if unit == "METER":
        raise ValueError(
            "Для услуги с тарификацией за пог. м укажите количество вручную"
        )
    return Decimal("0")


class FeatureCostingEngine:
    """Чистое ядро Контура 1 (объёмно-поверхностный метод).

    To = Vrem / (Q * Kq) + Asurf_outer / (S_main * Ks) * KIT
         + Asurf_inner / (S_inner * Ks) * KIT + Σ Tсверления
    Tшт = To * (1 + alpha)                          alpha ≈ 8%
    Cmat = Mgross * Pmat - (Mgross - Mnet) * Kсбора * Pscrap
    Ccoop = Σ qty_i(unit, MOQ/batch) * price_i      (термо за кг, гальв за дм²…)
    Price = (Cmat + Ccoop + ΣСтанок + Ctool + Cспец/N)
            * (1 + margin_percent * Kmargin(Ugroup) / 100)   APS-динамика
    Floor = Cmat + Ccoop + ΣTo_i·R_i + труд + Ctool   переменные издержки:
            без α, Tпз и спец-оснастки — ниже цены не бывает (антидемпинг)
    """

    @staticmethod
    def calculate(
        request: CalculateRequestDTO,
        rates: MasterDataRates,
        geometry_override: geometry.GeometryMetrics | None = None,
    ) -> CalculationResultDTO:
        # SCAD-режим: готовые метрики из STL-сетки вместо аналитики шаблона
        geo = (
            geometry_override
            if geometry_override is not None
            else geometry.net_metrics(request)
        )
        v_removed = geo.v_gross_mm3 - geo.v_net_mm3
        kq = float(request.material.k_mach_rough)
        ks = float(request.material.k_mach_finish)
        density = float(request.material.density_g_cm3)
        alpha = 1.0 + geometry.OVERHEAD_PERCENT / 100.0

        t_rough = v_removed / 1000.0 / (rates.main.q_rough_cm3_min * kq)
        t_finish_outer = (
            (geo.a_outer_mm2 / 10000.0)
            / (rates.main.s_finish_dm2_min * ks)
            * rates.kit_multiplier
        )
        s_inner = (
            rates.inner.s_finish_dm2_min
            if rates.inner is not None
            else rates.main.s_finish_dm2_min
        )
        t_finish_inner = (
            (geo.a_inner_mm2 / 10000.0) / (s_inner * ks) * rates.kit_multiplier
        )

        t_drill = 0.0
        tool_drill_cost = 0.0
        kwear = float(request.material.tool_wear)
        for feature in request.features:
            if isinstance(feature, HoleArrayFeature):
                feed = _drill_feed(feature, rates.drilling_bands)
                if feed is not None and feed > 0:
                    feature_time = (
                        feature.count
                        * geometry.drilling_depth_mm(feature)
                        / (feed * kq)
                    )
                    t_drill += feature_time
                    basket = _drill_basket_for(feature, rates.drill_baskets)
                    if basket is not None:
                        tool_drill_cost += (
                            feature_time
                            * _basket_minute_cost(basket)
                            * kwear
                            * TOOL_SCRAP_FACTOR
                        )

        tool_main_cost = 0.0
        if rates.main_basket is not None:
            tool_main_cost = (
                (t_rough + t_finish_outer)
                * _basket_minute_cost(rates.main_basket)
                * kwear
                * TOOL_SCRAP_FACTOR
            )
        tool_inner_cost = 0.0
        if rates.inner_basket is not None and rates.inner is not None:
            tool_inner_cost = (
                t_finish_inner
                * _basket_minute_cost(rates.inner_basket)
                * kwear
                * TOOL_SCRAP_FACTOR
            )
        tool_cost = tool_main_cost + tool_inner_cost + tool_drill_cost

        main_time = (t_rough + t_finish_outer + t_drill) * alpha
        if rates.inner is None:
            main_time += t_finish_inner * alpha
            inner_time = 0.0
        else:
            inner_time = t_finish_inner * alpha
        machine_time = main_time + inner_time
        setup_total = rates.main.setup_time_min + (
            rates.inner.setup_time_min if rates.inner is not None else 0.0
        )

        m_net = geo.v_net_mm3 * density / 1_000_000.0
        m_gross = geo.v_gross_mm3 * density / 1_000_000.0
        material_cost = m_gross * float(request.material.cost_per_kg) - (
            m_gross - m_net
        ) * geometry.SCRAP_RECOVERY * float(request.material.scrap_price_per_kg)

        batch = request.batch_size
        main_rate = float(rates.main.machine_rate_per_min)
        main_cost = (
            main_time * main_rate + (rates.main.setup_time_min / batch) * main_rate
        )
        if rates.inner is not None:
            inner_rate = float(rates.inner.machine_rate_per_min)
            inner_cost = (
                inner_time * inner_rate
                + (rates.inner.setup_time_min / batch) * inner_rate
            )
        else:
            inner_cost = 0.0
        aux_cost = sum(
            aux.fixed_time_min * float(aux.rate_per_min) for aux in rates.auxiliary
        )
        machine_cost = main_cost + inner_cost + aux_cost
        special_tool_per_part = float(request.special_tool_cost) / batch

        # Кооперация (Ccoop): qty на деталь по единице тарификации,
        # MOQ амортизируется на партию (min_lot / batch на деталь).
        coop_by_id = {rate.service_id: rate for rate in rates.cooperation}
        cooperation_lines: list[CooperationBreakdownDTO] = []
        cooperation_cost = 0.0
        area_dm2 = (geo.a_outer_mm2 + geo.a_inner_mm2) / 10000.0
        for line in request.cooperation:
            rate = coop_by_id.get(line.service_id)
            if rate is None:
                continue
            qty = _cooperation_qty(rate.unit, m_net, area_dm2, line.qty_override)
            moq_per_part = float(rate.min_lot_qty) / batch
            qty_effective = Decimal(str(max(float(qty), moq_per_part)))
            line_cost = float(qty_effective * rate.price_per_unit)
            cooperation_cost += line_cost
            cooperation_lines.append(
                CooperationBreakdownDTO(
                    name=rate.name,
                    unit=rate.unit,
                    qty=qty_effective.quantize(Decimal("0.001")),
                    unit_price=rate.price_per_unit,
                    cost=_money(line_cost),
                )
            )

        # Floor Price (docx, защита от демпинга): переменные издержки —
        # только основное машинное время To (без α и Tпз), материал,
        # кооперация, труд aux; tool_cost уже содержит ×1.05.
        inner_floor_rate = (
            float(rates.inner.machine_rate_per_min)
            if rates.inner is not None
            else main_rate
        )
        floor_price = (
            material_cost
            + cooperation_cost
            + (t_rough + t_finish_outer + t_drill) * main_rate
            + t_finish_inner * inner_floor_rate
            + aux_cost
            + tool_cost
        )

        production_cost = (
            material_cost
            + machine_cost
            + tool_cost
            + special_tool_per_part
            + cooperation_cost
        )
        margin = float(request.margin_percent) / 100.0 * rates.margin_multiplier
        price_per_part = production_cost * (1.0 + margin)

        operations = [
            OperationBreakdownDTO(
                code=rates.main.code,
                name=rates.main.name,
                machine_time_min=round(main_time, 3),
                setup_time_min=rates.main.setup_time_min,
                machine_rate_per_min=rates.main.machine_rate_per_min,
                cost=_money(main_cost),
                tool_cost=_money(tool_main_cost + tool_drill_cost),
            )
        ]
        if rates.inner is not None:
            operations.append(
                OperationBreakdownDTO(
                    code=rates.inner.code,
                    name=rates.inner.name,
                    machine_time_min=round(inner_time, 3),
                    setup_time_min=rates.inner.setup_time_min,
                    machine_rate_per_min=rates.inner.machine_rate_per_min,
                    cost=_money(inner_cost),
                    tool_cost=_money(tool_inner_cost),
                )
            )
        for aux in rates.auxiliary:
            operations.append(
                OperationBreakdownDTO(
                    code=aux.code,
                    name=aux.name,
                    machine_time_min=aux.fixed_time_min,
                    setup_time_min=0.0,
                    machine_rate_per_min=aux.rate_per_min,
                    cost=_money(aux.fixed_time_min * float(aux.rate_per_min)),
                )
            )

        return CalculationResultDTO(
            v_net_cm3=round(geo.v_net_mm3 / 1000.0, 3),
            v_gross_cm3=round(geo.v_gross_mm3 / 1000.0, 3),
            v_removed_cm3=round(v_removed / 1000.0, 3),
            m_net_kg=round(m_net, 3),
            m_gross_kg=round(m_gross, 3),
            material_cost=_money(material_cost),
            machine_time_min=round(machine_time, 3),
            setup_time_min=setup_total,
            price_per_part=_money(price_per_part),
            batch_total_price=_money(price_per_part * batch),
            tool_cost=_money(tool_cost),
            cooperation_cost=_money(cooperation_cost),
            operations=operations,
            cooperations=cooperation_lines,
            margin_multiplier=rates.margin_multiplier,
            capacity_utilization_percent=rates.capacity_utilization_percent,
            bottleneck_group=rates.bottleneck_group,
            floor_price_per_part=_money(floor_price),
        )


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
