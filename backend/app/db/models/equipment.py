from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy import Enum as SaEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import MachineType


class WorkCenter(Base, TimestampMixin):
    __tablename__ = "work_centers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    machine_type: Mapped[MachineType] = mapped_column(
        SaEnum(MachineType, native_enum=False, length=30)
    )
    group_code: Mapped[str] = mapped_column(String(50), index=True)
    workspace_x_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), default=None)
    workspace_y_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), default=None)
    workspace_z_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), default=None)
    spindle_power_kw: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2), default=None
    )
    max_rpm: Mapped[int | None] = mapped_column(Integer, default=None)
    base_setup_time_min: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), default=Decimal("0.00")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    financial_profile: Mapped["MachineFinancialProfile | None"] = relationship(
        back_populates="work_center", uselist=False
    )


class MachineFinancialProfile(Base, TimestampMixin):
    __tablename__ = "machine_financial_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_center_id: Mapped[int] = mapped_column(
        ForeignKey("work_centers.id", ondelete="CASCADE"), unique=True
    )
    machine_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00")
    )
    depreciation_years: Mapped[int] = mapped_column(Integer, default=10)
    energy_cost_per_hour: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    operator_rate_per_hour: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    multi_machine_factor: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("1.00")
    )
    shop_overhead_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )
    plant_overhead_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )
    machine_rate_per_min: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0.0000")
    )
    valid_from: Mapped[date] = mapped_column(Date, default=date.today)

    work_center: Mapped[WorkCenter] = relationship(back_populates="financial_profile")
