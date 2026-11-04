"""SCAD-режим расчёта: подмена геометрии метриками STL-сетки.

Домен остаётся чистым: сетку меряет инфраструктура (app/services/scad_compiler)
и передаёт сюда неизменяемый MeshMeasurements. Правила слияния с аналитикой:

- v_net и полная площадь — из сетки (реальная геометрия пользователя);
- v_gross — аналитическая заготовка с припусками (geometry.py), золотые
  числа TEMPLATE-режима не зависят от способа компиляции;
- a_inner — боковая поверхность отверстий (HOLE_ARRAY) и центральной
  расточки (T2 inner_steps / T3 center hole): именно она тарифицируется
  INNER_OPERATION, а «конверт заготовки» технологически внутренней
  поверхностью не является.
"""

import math
from dataclasses import dataclass

from app.domain.dto.calculation import (
    CalculateRequestDTO,
    HoleArrayFeature,
    T2Template,
    T3Template,
)
from app.domain.engine import geometry
from app.domain.engine.geometry import GeometryMetrics


@dataclass(frozen=True)
class MeshMeasurements:
    """Метрики прекомпилированной STL-сетки (мм, мм², мм³)."""

    extents_mm: tuple[float, float, float]
    volume_mm3: float
    area_mm2: float


def _holes_inner_area_mm2(request: CalculateRequestDTO) -> float:
    return sum(
        feature.count * math.pi * feature.diameter * feature.depth
        for feature in request.features
        if isinstance(feature, HoleArrayFeature)
    )


def _bore_inner_area_mm2(request: CalculateRequestDTO) -> float:
    template = request.base_template
    if isinstance(template, T2Template):
        return sum(
            math.pi * step.diameter * step.length
            for step in template.dimensions.inner_steps
        )
    if isinstance(template, T3Template):
        center = template.dimensions.center_hole_diameter
        return math.pi * center * template.dimensions.thickness
    return 0.0


def build_geometry_override(
    request: CalculateRequestDTO, mesh: MeshMeasurements
) -> GeometryMetrics:
    """Метрики расчёта для запроса с scad_code.

    Raises:
        ValueError: сетка противоречит шаблону (v_net > v_gross заготовки
            или площадь сетки меньше суммарной площади отверстий).
    """
    analytic = geometry.net_metrics(request)
    a_inner = _holes_inner_area_mm2(request) + _bore_inner_area_mm2(request)
    a_outer = mesh.area_mm2 - a_inner
    if mesh.volume_mm3 <= 0:
        raise ValueError("Сетка пуста: v_net должен быть положительным")
    if a_outer < 0:
        raise ValueError(
            "Площадь сетки меньше суммарной площади отверстий и расточки — "
            "проверьте соответствие scad_code и base_template"
        )
    if analytic.v_gross_mm3 < mesh.volume_mm3:
        raise ValueError(
            "v_net сетки больше аналитической заготовки (v_gross) — "
            "увеличьте габариты base_template до bbox модели"
        )
    return GeometryMetrics(
        v_net_mm3=mesh.volume_mm3,
        v_gross_mm3=analytic.v_gross_mm3,
        a_surf_mm2=mesh.area_mm2,
        a_outer_mm2=a_outer,
        a_inner_mm2=a_inner,
    )
