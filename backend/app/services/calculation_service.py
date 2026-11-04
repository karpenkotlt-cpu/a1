from decimal import Decimal

from app.core.config import settings
from app.db.models import ToolBasket as ToolBasketRow
from app.db.models.enums import CoefficientType
from app.domain.dto.calculation import (
    BatchPriceDTO,
    CalculateRequestDTO,
    CalculationResultDTO,
)
from app.domain.engine import geometry, scad_metrics
from app.domain.engine.aps import get_dynamic_margin_multiplier
from app.domain.engine.costing import (
    AuxiliaryRate,
    CooperationRate,
    DrillingBand,
    FeatureCostingEngine,
    MasterDataRates,
    OperationRates,
    ToolBasketRate,
)
from app.repositories.uow import UnitOfWork
from app.services import scad_compiler

TEMPLATE_OPERATION = {
    "T1_STEPPED_SHAFT": "TURN_CNC_EXT",
    "T2_BUSHING": "TURN_CNC_EXT",
    "T3_FLANGE": "TURN_CNC_EXT",
    "T4_PLATE": "MILL_CNC_FACE",
    "T5_HOUSING": "MILL_CNC_FACE",
}

INNER_OPERATION = {
    "T2_BUSHING": "TURN_CNC_INT",
}

DEFAULT_TOLERANCE_MULTIPLIER = 1.0

LADDER_BATCHES = (1, 5, 10, 25, 50, 100)

COOPERATION_TYPE_TITLES = {
    "HEAT_TREATMENT": "Термообработка",
    "GALVANIZING": "Гальваника",
    "ANODIZING": "Анодирование",
    "LASER_CUT": "Лазерная резка",
    "PAINTING": "Окраска",
}


def _to_basket_rate(basket: ToolBasketRow) -> ToolBasketRate:
    return ToolBasketRate(
        operation_group=basket.operation_group,
        tool_set_cost=basket.tool_set_cost,
        tool_life_min=float(basket.tool_life_min),
        regrindable=basket.regrindable,
        diameter_from_mm=(
            float(basket.diameter_from_mm)
            if basket.diameter_from_mm is not None
            else None
        ),
        diameter_to_mm=(
            float(basket.diameter_to_mm) if basket.diameter_to_mm is not None else None
        ),
    )


class CalculationDataError(Exception):
    pass


class CalculationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def _operation_rates(self, code: str) -> OperationRates | None:
        operation = await self._uow.operations.get_by_code(code)
        if operation is None:
            return None
        base_rate = await self._uow.operations.get_base_rate(operation.id)
        if base_rate is None:
            return None
        machine_rate = await self._uow.work_centers.get_rate_for_group(
            operation.work_center_group
        )
        if machine_rate is None or machine_rate <= Decimal("0"):
            return None
        return OperationRates(
            code=operation.code,
            name=operation.name,
            q_rough_cm3_min=float(base_rate.q_rough_cm3_min),
            s_finish_dm2_min=float(base_rate.s_finish_dm2_min),
            setup_time_min=float(operation.setup_time_base_min),
            machine_rate_per_min=machine_rate,
            work_center_group=operation.work_center_group,
        )

    async def _basket_for(self, operation_group: str) -> ToolBasketRate | None:
        basket = await self._uow.tool_baskets.get_for_operation(operation_group)
        return None if basket is None else _to_basket_rate(basket)

    async def _cooperation_rates(
        self, request: CalculateRequestDTO
    ) -> tuple[CooperationRate, ...]:
        """Резолвит выбранные услуги из справочника (цены — только из БД)."""
        rates: list[CooperationRate] = []
        for line in request.cooperation:
            row = await self._uow.cooperation_services.get(line.service_id)
            if row is None:
                raise CalculationDataError(
                    f"Услуга кооперации id={line.service_id} не найдена"
                )
            title = COOPERATION_TYPE_TITLES.get(
                row.service_type.value, row.service_type.value
            )
            name = f"{title} ({row.contractor})" if row.contractor else title
            rates.append(
                CooperationRate(
                    service_id=row.id,
                    name=name,
                    unit=row.unit.value,
                    price_per_unit=row.price_per_unit,
                    min_lot_qty=row.min_lot_qty,
                )
            )
        return tuple(rates)

    async def calculate(self, request: CalculateRequestDTO) -> CalculationResultDTO:
        rates = await self._build_rates(request)
        geometry_override = await self._geometry_override(request)
        return self._run(request, rates, geometry_override)

    async def ladder(self, request: CalculateRequestDTO) -> list[BatchPriceDTO]:
        """Цены по тиражам: rates собираются один раз, движок чистый —
        гоняется для каждого тиража (Tпз и MOQ кооперации амортизируются).
        SCAD компилируется ОДИН раз на запрос, а не в каждом прогоне."""
        rates = await self._build_rates(request)
        geometry_override = await self._geometry_override(request)
        batches = sorted({*LADDER_BATCHES, request.batch_size})
        rows: list[BatchPriceDTO] = []
        for batch in batches:
            result = self._run(
                request.model_copy(update={"batch_size": batch}),
                rates,
                geometry_override,
            )
            rows.append(
                BatchPriceDTO(
                    batch_size=batch,
                    price_per_part=result.price_per_part,
                    batch_total_price=result.batch_total_price,
                )
            )
        return rows

    async def _geometry_override(
        self, request: CalculateRequestDTO
    ) -> geometry.GeometryMetrics | None:
        """SCAD-режим: сетка пользователя подменяет аналитическую геометрию.
        Kill-switch APP_OPENSCAD_ENABLED=false — тихий фолбэк на TEMPLATE."""
        if not request.scad_code or not settings.openscad_enabled:
            return None
        try:
            _, mesh = await scad_compiler.compile_and_measure(request.scad_code)
        except scad_compiler.ScadUnavailableError as exc:
            raise CalculationDataError(str(exc)) from exc
        except scad_compiler.ScadCompileError as exc:
            raise CalculationDataError(str(exc)) from exc
        try:
            return scad_metrics.build_geometry_override(request, mesh)
        except ValueError as exc:
            raise CalculationDataError(str(exc)) from exc

    def _run(
        self,
        request: CalculateRequestDTO,
        rates: MasterDataRates,
        geometry_override: geometry.GeometryMetrics | None = None,
    ) -> CalculationResultDTO:
        try:
            return FeatureCostingEngine.calculate(request, rates, geometry_override)
        except ValueError as exc:
            raise CalculationDataError(str(exc)) from exc

    async def _build_rates(self, request: CalculateRequestDTO) -> MasterDataRates:
        template_type = str(request.base_template.type)
        operation_code = TEMPLATE_OPERATION[template_type]
        main_rates = await self._operation_rates(operation_code)
        if main_rates is None:
            raise CalculationDataError(
                f"Операция {operation_code} не настроена "
                "(нет Q/S или ставки группы станков)"
            )

        inner_code = INNER_OPERATION.get(template_type)
        inner_rates = await self._operation_rates(inner_code) if inner_code else None

        kit = DEFAULT_TOLERANCE_MULTIPLIER
        for feature in request.features:
            tolerance = getattr(feature, "tolerance", "IT11")
            multiplier = await self._uow.coefficients.get_multiplier(
                CoefficientType.TOLERANCE, tolerance
            )
            if multiplier is not None and multiplier > kit:
                kit = multiplier

        drilling_rows = await self._uow.drilling_rates.list_all()
        bands = tuple(
            DrillingBand(
                diameter_from_mm=float(row.diameter_from_mm),
                diameter_to_mm=float(row.diameter_to_mm),
                carbide_feed_mm_min=float(row.carbide_feed_mm_min),
                hss_feed_mm_min=float(row.hss_feed_mm_min),
            )
            for row in drilling_rows
        )
        auxiliary_rows = await self._uow.auxiliary_operations.list_active()
        auxiliary = tuple(
            AuxiliaryRate(
                code=row.code,
                name=row.name,
                fixed_time_min=float(row.fixed_time_min),
                rate_per_min=row.rate_per_min,
            )
            for row in auxiliary_rows
        )

        # Динамическая маржа APS: узкое место = max(Ugroup) по всем группам
        # маршрута (главный станок + расточка). utilization в Python:
        # GENERATED-колонка в SQLite делит целочисленно.
        route_groups = {main_rates.work_center_group}
        if inner_rates is not None:
            route_groups.add(inner_rates.work_center_group)
        utilization: float | None = None
        bottleneck_group: str | None = None
        for group in sorted(route_groups):
            capacity = await self._uow.capacity_loads.get_by_group(group)
            if capacity is None or capacity.total_fund_minutes in (None, 0):
                continue
            group_utilization = (
                float(capacity.scheduled_minutes)
                / float(capacity.total_fund_minutes)
                * 100.0
            )
            if utilization is None or group_utilization > utilization:
                utilization = group_utilization
                bottleneck_group = group

        return MasterDataRates(
            main=main_rates,
            inner=inner_rates,
            kit_multiplier=kit,
            drilling_bands=bands,
            auxiliary=auxiliary,
            main_basket=await self._basket_for(main_rates.code),
            inner_basket=(
                await self._basket_for(inner_rates.code)
                if inner_rates is not None
                else None
            ),
            drill_baskets=tuple(
                _to_basket_rate(row)
                for row in await self._uow.tool_baskets.list_drill_baskets()
            ),
            cooperation=await self._cooperation_rates(request),
            margin_multiplier=(
                get_dynamic_margin_multiplier(utilization)
                if utilization is not None
                else 1.0
            ),
            capacity_utilization_percent=utilization,
            bottleneck_group=bottleneck_group,
        )
