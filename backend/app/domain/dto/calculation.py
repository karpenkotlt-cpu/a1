from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MaterialInputDTO(BaseModel):
    iso_group: str = Field(pattern=r"^[PMKNSH]$")
    k_mach_rough: Decimal = Field(gt=0)
    k_mach_finish: Decimal = Field(gt=0)
    density_g_cm3: Decimal = Field(gt=0)
    cost_per_kg: Decimal = Field(ge=0)
    scrap_price_per_kg: Decimal = Field(default=Decimal("0.00"), ge=0)
    tool_wear: Decimal = Field(default=Decimal("1.00"), gt=0)


class StepDTO(BaseModel):
    diameter: float = Field(gt=0)
    length: float = Field(gt=0)


class T1Dimensions(BaseModel):
    steps: list[StepDTO] = Field(min_length=1)


class T2Dimensions(BaseModel):
    outer_steps: list[StepDTO] = Field(min_length=1)
    inner_steps: list[StepDTO] = Field(default_factory=list)


class T3Dimensions(BaseModel):
    outer_diameter: float = Field(gt=0)
    thickness: float = Field(gt=0)
    center_hole_diameter: float = Field(default=0.0, ge=0)


class T4Dimensions(BaseModel):
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class T5Dimensions(BaseModel):
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    removal_ratio: float = Field(gt=0, le=0.95)


class T1Template(BaseModel):
    type: Literal["T1_STEPPED_SHAFT"]
    dimensions: T1Dimensions


class T2Template(BaseModel):
    type: Literal["T2_BUSHING"]
    dimensions: T2Dimensions


class T3Template(BaseModel):
    type: Literal["T3_FLANGE"]
    dimensions: T3Dimensions


class T4Template(BaseModel):
    type: Literal["T4_PLATE"]
    dimensions: T4Dimensions


class T5Template(BaseModel):
    type: Literal["T5_HOUSING"]
    dimensions: T5Dimensions


BaseTemplate = Annotated[
    T1Template | T2Template | T3Template | T4Template | T5Template,
    Field(discriminator="type"),
]


class HoleArrayFeature(BaseModel):
    type: Literal["HOLE_ARRAY"]
    count: int = Field(ge=1)
    diameter: float = Field(gt=0)
    depth: float = Field(gt=0)
    is_through: bool = False
    tolerance: str = Field(default="IT11", pattern=r"^IT\d{1,2}(-\d{1,2})?$")
    thread: str | None = None
    counterbore_diameter: float | None = Field(default=None, gt=0)
    counterbore_depth: float | None = Field(default=None, gt=0)
    drill_type: Literal["CARBIDE", "HSS"] = "CARBIDE"


class RectPocketFeature(BaseModel):
    type: Literal["RECT_POCKET"]
    count: int = Field(ge=1)
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    depth: float = Field(gt=0)
    tool_diameter: float = Field(default=10.0, gt=0)
    tolerance: str = Field(default="IT11", pattern=r"^IT\d{1,2}(-\d{1,2})?$")


Feature = Annotated[
    HoleArrayFeature | RectPocketFeature,
    Field(discriminator="type"),
]


class CalculateRequestDTO(BaseModel):
    project_id: UUID
    batch_size: int = Field(default=1, ge=1)
    material: MaterialInputDTO
    base_template: BaseTemplate
    features: list[Feature] = Field(default_factory=list)
    margin_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=200)
    special_tool_cost: Decimal = Field(default=Decimal("0.00"), ge=0)
    cooperation: list["CooperationLineDTO"] = Field(default_factory=list)
    # Код OpenSCAD: при наличии геометрия берётся из STL-сетки (GeometryOverride),
    # аналитика TEMPLATE-режима остаётся фолбэком. Старые снапшоты валидны.
    scad_code: str | None = Field(default=None, max_length=100_000)


class CooperationLineDTO(BaseModel):
    """Выбранная услуга кооперации; qty_override заменяет авто-количество."""

    service_id: int
    qty_override: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=3
    )


class OperationBreakdownDTO(BaseModel):
    code: str
    name: str
    machine_time_min: float
    setup_time_min: float
    machine_rate_per_min: Decimal
    cost: Decimal
    tool_cost: Decimal = Decimal("0.00")


class CooperationBreakdownDTO(BaseModel):
    name: str
    unit: str
    qty: Decimal
    unit_price: Decimal
    cost: Decimal


class BatchPriceDTO(BaseModel):
    """Ступень лестницы тиражей: цена с учётом амортизации Tпз и MOQ."""

    batch_size: int
    price_per_part: Decimal
    batch_total_price: Decimal


class CalculationResultDTO(BaseModel):
    v_net_cm3: float
    v_gross_cm3: float
    v_removed_cm3: float
    m_net_kg: float
    m_gross_kg: float
    material_cost: Decimal
    machine_time_min: float
    setup_time_min: float
    price_per_part: Decimal
    batch_total_price: Decimal
    tool_cost: Decimal = Decimal("0.00")
    cooperation_cost: Decimal = Decimal("0.00")
    operations: list[OperationBreakdownDTO] = Field(default_factory=list)
    cooperations: list[CooperationBreakdownDTO] = Field(default_factory=list)
    margin_multiplier: float = 1.0
    capacity_utilization_percent: float | None = None
    bottleneck_group: str | None = None
    floor_price_per_part: Decimal | None = None
