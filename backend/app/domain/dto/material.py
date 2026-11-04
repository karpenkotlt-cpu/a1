from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MaterialBase(BaseModel):
    grade: str = Field(min_length=2, max_length=100)
    gost: str | None = Field(default=None, max_length=50)
    iso_group: str = Field(pattern=r"^[PMKNSH]$")
    density_g_cm3: Decimal = Field(gt=0, max_digits=6, decimal_places=4)
    machinability_factor: Decimal = Field(gt=0, max_digits=4, decimal_places=2)
    cost_per_kg: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    scrap_price_per_kg: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    grade: str | None = Field(default=None, min_length=2, max_length=100)
    gost: str | None = Field(default=None, max_length=50)
    iso_group: str | None = Field(default=None, pattern=r"^[PMKNSH]$")
    density_g_cm3: Decimal | None = Field(
        default=None, gt=0, max_digits=6, decimal_places=4
    )
    machinability_factor: Decimal | None = Field(
        default=None, gt=0, max_digits=4, decimal_places=2
    )
    cost_per_kg: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    scrap_price_per_kg: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )


class MaterialRead(MaterialBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    k_mach_finish: Decimal | None = None
    tool_wear: Decimal | None = None
