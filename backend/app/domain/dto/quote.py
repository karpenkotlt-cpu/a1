from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.dto.calculation import (
    CalculateRequestDTO,
    CalculationResultDTO,
)


class QuoteCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    material_id: int | None = None
    request: CalculateRequestDTO


class QuoteReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_id: str
    batch_size: int
    material_id: int | None
    price_per_part: Decimal
    batch_total_price: Decimal
    author_email: str
    created_at: datetime


class QuoteDetailDTO(QuoteReadDTO):
    request: CalculateRequestDTO
    result: CalculationResultDTO


TURNED_TEMPLATES = {"T1_STEPPED_SHAFT", "T2_BUSHING", "T3_FLANGE"}


class AnalogueQueryDTO(BaseModel):
    """Поиск аналогов: тот же шаблон, близкий габарит, та же ISO-группа.

    Токарные (T1-T3) задаются (d_max, length), коробки (T4/T5) —
    (length, width, height); макс. отклонение по любой оси ≤ tolerance.
    """

    template_type: str
    iso_group: str | None = None
    d_max_mm: float | None = Field(default=None, gt=0)
    length_mm: float | None = Field(default=None, gt=0)
    width_mm: float | None = Field(default=None, gt=0)
    height_mm: float | None = Field(default=None, gt=0)
    tolerance_percent: float = Field(default=35.0, gt=0, le=200)
    limit: int = Field(default=5, ge=1, le=20)


class AnalogueRowDTO(BaseModel):
    quote_id: int
    name: str
    batch_size: int
    price_per_part: Decimal
    author_email: str
    created_at: datetime
    deviation_percent: float
