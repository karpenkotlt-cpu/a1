import math
from dataclasses import dataclass

from app.domain.dto.calculation import (
    CalculateRequestDTO,
    HoleArrayFeature,
    RectPocketFeature,
    T1Template,
    T2Template,
    T3Template,
    T4Template,
    T5Template,
)

RADIAL_ALLOWANCE_MM = 2.5
FACE_ALLOWANCE_MM = 2.5
CUT_WIDTH_MM = 3.0
SCRAP_RECOVERY = 0.7
OVERHEAD_PERCENT = 8.0
DRILL_APPROACH_MM = 2.0

ROUND_DIGITS = 3


@dataclass(frozen=True)
class GeometryMetrics:
    v_net_mm3: float
    v_gross_mm3: float
    a_surf_mm2: float
    a_outer_mm2: float = 0.0
    a_inner_mm2: float = 0.0


def _rotation_volume_mm3(steps: list[tuple[float, float]]) -> float:
    return sum(math.pi / 4.0 * (d * d) * length for d, length in steps)


def _hole_volume_mm3(feature: HoleArrayFeature) -> float:
    volume = feature.count * math.pi / 4.0 * feature.diameter**2 * feature.depth
    if feature.counterbore_diameter and feature.counterbore_depth:
        volume += (
            feature.count
            * math.pi
            / 4.0
            * (feature.counterbore_diameter**2 - feature.diameter**2)
            * feature.counterbore_depth
        )
    return volume


def _pocket_volume_mm3(feature: RectPocketFeature) -> float:
    return feature.count * feature.length * feature.width * feature.depth


def _features_volume_mm3(request: CalculateRequestDTO) -> float:
    total = 0.0
    for feature in request.features:
        if isinstance(feature, HoleArrayFeature):
            total += _hole_volume_mm3(feature)
        else:
            total += _pocket_volume_mm3(feature)
    return total


def _t1_metrics(template: T1Template, features_volume: float) -> GeometryMetrics:
    steps = [(s.diameter, s.length) for s in template.dimensions.steps]
    v_base = _rotation_volume_mm3(steps)
    d_max = max(d for d, _ in steps)
    total_l = sum(length for _, length in steps)
    v_gross = (
        math.pi
        / 4.0
        * (d_max + 2 * RADIAL_ALLOWANCE_MM) ** 2
        * (total_l + 2 * FACE_ALLOWANCE_MM + CUT_WIDTH_MM)
    )
    a_side = sum(math.pi * d * length for d, length in steps)
    a_faces = math.pi / 4.0 * (steps[0][0] ** 2 + steps[-1][0] ** 2)
    a_outer = a_side + a_faces
    return GeometryMetrics(
        v_net_mm3=v_base - features_volume,
        v_gross_mm3=v_gross,
        a_surf_mm2=a_outer,
        a_outer_mm2=a_outer,
    )


def _t2_metrics(template: T2Template, features_volume: float) -> GeometryMetrics:
    outer = [(s.diameter, s.length) for s in template.dimensions.outer_steps]
    inner = [(s.diameter, s.length) for s in template.dimensions.inner_steps]
    v_base = _rotation_volume_mm3(outer) - _rotation_volume_mm3(inner)
    d_max = max(d for d, _ in outer)
    total_l = sum(length for _, length in outer)
    v_gross = (
        math.pi
        / 4.0
        * (d_max + 2 * RADIAL_ALLOWANCE_MM) ** 2
        * (total_l + 2 * FACE_ALLOWANCE_MM + CUT_WIDTH_MM)
    )
    a_side_outer = sum(math.pi * d * length for d, length in outer)
    a_side_inner = sum(math.pi * d * length for d, length in inner)
    a_faces = math.pi / 4.0 * (outer[0][0] ** 2 + outer[-1][0] ** 2)
    a_outer = a_side_outer + a_faces
    return GeometryMetrics(
        v_net_mm3=v_base - features_volume,
        v_gross_mm3=v_gross,
        a_surf_mm2=a_outer + a_side_inner,
        a_outer_mm2=a_outer,
        a_inner_mm2=a_side_inner,
    )


def _t3_metrics(template: T3Template, features_volume: float) -> GeometryMetrics:
    d = template.dimensions.outer_diameter
    t = template.dimensions.thickness
    d_center = template.dimensions.center_hole_diameter
    v_base = math.pi / 4.0 * (d * d - d_center * d_center) * t
    v_gross = (
        math.pi
        / 4.0
        * (d + 2 * RADIAL_ALLOWANCE_MM) ** 2
        * (t + 2 * FACE_ALLOWANCE_MM + CUT_WIDTH_MM)
    )
    a_outer = math.pi * d * t + 2.0 * math.pi / 4.0 * (d * d - d_center * d_center)
    a_inner = math.pi * d_center * t
    return GeometryMetrics(
        v_net_mm3=v_base - features_volume,
        v_gross_mm3=v_gross,
        a_surf_mm2=a_outer + a_inner,
        a_outer_mm2=a_outer,
        a_inner_mm2=a_inner,
    )


def _t4_metrics(template: T4Template, features_volume: float) -> GeometryMetrics:
    length = template.dimensions.length
    width = template.dimensions.width
    height = template.dimensions.height
    v_base = length * width * height
    a = RADIAL_ALLOWANCE_MM + FACE_ALLOWANCE_MM - CUT_WIDTH_MM
    v_gross = (length + 2 * a) * (width + 2 * a) * (height + 2 * a)
    a_surf = 2.0 * (length * width + length * height + width * height)
    return GeometryMetrics(
        v_net_mm3=v_base - features_volume,
        v_gross_mm3=v_gross,
        a_surf_mm2=a_surf,
        a_outer_mm2=a_surf,
    )


def _t5_metrics(template: T5Template, features_volume: float) -> GeometryMetrics:
    length = template.dimensions.length
    width = template.dimensions.width
    height = template.dimensions.height
    v_base = length * width * height * (1.0 - template.dimensions.removal_ratio)
    a = RADIAL_ALLOWANCE_MM + FACE_ALLOWANCE_MM - CUT_WIDTH_MM
    v_gross = (length + 2 * a) * (width + 2 * a) * (height + 2 * a)
    a_surf = 2.0 * (length * width + length * height + width * height)
    return GeometryMetrics(
        v_net_mm3=v_base - features_volume,
        v_gross_mm3=v_gross,
        a_surf_mm2=a_surf,
        a_outer_mm2=a_surf,
    )


def net_metrics(request: CalculateRequestDTO) -> GeometryMetrics:
    """CSG: Vnet = Vbase − Σ Vfeatures; Vgross = заготовка с припусками."""
    features_volume = _features_volume_mm3(request)
    template = request.base_template
    if isinstance(template, T1Template):
        return _t1_metrics(template, features_volume)
    if isinstance(template, T2Template):
        return _t2_metrics(template, features_volume)
    if isinstance(template, T3Template):
        return _t3_metrics(template, features_volume)
    if isinstance(template, T5Template):
        return _t5_metrics(template, features_volume)
    return _t4_metrics(template, features_volume)


def drilling_depth_mm(feature: HoleArrayFeature) -> float:
    return feature.depth + DRILL_APPROACH_MM
