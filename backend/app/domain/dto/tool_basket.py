from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ToolBasketReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_group: str
    material_iso_group: str
    tool_set_cost: Decimal
    tool_life_min: Decimal
    regrindable: bool
    diameter_from_mm: Decimal | None
    diameter_to_mm: Decimal | None


class ToolBasketUpdateDTO(BaseModel):
    tool_set_cost: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    tool_life_min: Decimal | None = Field(
        default=None, gt=0, max_digits=8, decimal_places=2
    )
    regrindable: bool | None = None
