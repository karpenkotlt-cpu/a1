from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import CooperationServiceType, PriceUnit


class OperationRateReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_iso_group: str
    q_rough_cm3_min: Decimal
    s_finish_dm2_min: Decimal


class OperationReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    operation_type: str
    work_center_group: str
    min_tool_diameter_mm: Decimal | None
    setup_time_base_min: Decimal
    rates: list[OperationRateReadDTO] = Field(default_factory=list)


class OperationUpdateDTO(BaseModel):
    setup_time_base_min: Decimal | None = Field(
        default=None, ge=0, max_digits=6, decimal_places=1
    )


class OperationRateUpdateDTO(BaseModel):
    q_rough_cm3_min: Decimal | None = Field(
        default=None, gt=0, max_digits=8, decimal_places=3
    )
    s_finish_dm2_min: Decimal | None = Field(
        default=None, gt=0, max_digits=8, decimal_places=3
    )


class WorkCenterReadDTO(BaseModel):
    id: int
    code: str
    name: str
    machine_type: str
    group_code: str
    is_active: bool
    machine_rate_per_min: Decimal | None
    operator_rate_per_hour: Decimal | None


class WorkCenterUpdateDTO(BaseModel):
    machine_rate_per_min: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=4
    )


class CoefficientReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    coef_type: str
    code: str
    multiplier: Decimal
    description: str | None


class CoefficientUpdateDTO(BaseModel):
    multiplier: Decimal | None = Field(
        default=None, gt=0, max_digits=5, decimal_places=3
    )


class AuxiliaryOperationReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    fixed_time_min: Decimal
    rate_per_min: Decimal
    is_active: bool


class AuxiliaryOperationUpdateDTO(BaseModel):
    fixed_time_min: Decimal | None = Field(
        default=None, ge=0, max_digits=6, decimal_places=2
    )
    rate_per_min: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=4
    )
    is_active: bool | None = None


class DrillingRateReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    diameter_from_mm: Decimal
    diameter_to_mm: Decimal
    carbide_feed_mm_min: Decimal
    hss_feed_mm_min: Decimal


class DrillingRateUpdateDTO(BaseModel):
    carbide_feed_mm_min: Decimal | None = Field(
        default=None, gt=0, max_digits=6, decimal_places=1
    )
    hss_feed_mm_min: Decimal | None = Field(
        default=None, gt=0, max_digits=6, decimal_places=1
    )


class CapacityLoadReadDTO(BaseModel):
    id: int
    work_center_group: str
    horizon_days: int
    total_fund_minutes: Decimal
    scheduled_minutes: Decimal
    utilization_percent: float | None


class CapacityLoadCreateDTO(BaseModel):
    work_center_group: str = Field(min_length=1, max_length=50)
    horizon_days: int = Field(default=30, ge=1, le=365)
    total_fund_minutes: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    scheduled_minutes: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2
    )


class CapacityLoadUpdateDTO(BaseModel):
    horizon_days: int | None = Field(default=None, ge=1, le=365)
    total_fund_minutes: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    scheduled_minutes: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )


class CooperationServiceReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_type: CooperationServiceType
    unit: PriceUnit
    price_per_unit: Decimal
    contractor: str | None
    min_lot_qty: Decimal


class CooperationServiceCreateDTO(BaseModel):
    service_type: CooperationServiceType
    unit: PriceUnit
    price_per_unit: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    contractor: str | None = Field(default=None, max_length=100)
    min_lot_qty: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2
    )


class CooperationServiceUpdateDTO(BaseModel):
    service_type: CooperationServiceType | None = None
    unit: PriceUnit | None = None
    price_per_unit: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    contractor: str | None = Field(default=None, max_length=100)
    min_lot_qty: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
