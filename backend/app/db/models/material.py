from decimal import Decimal

from sqlalchemy import Enum as SaEnum
from sqlalchemy import (
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import MaterialProfile


class Material(Base, TimestampMixin):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    grade: Mapped[str] = mapped_column(String(100), unique=True)
    gost: Mapped[str | None] = mapped_column(String(50), default=None)
    iso_group: Mapped[str] = mapped_column(String(1))
    density_g_cm3: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    machinability_factor: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    cost_per_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    scrap_price_per_kg: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )

    assortment: Mapped[list["MaterialAssortment"]] = relationship(
        back_populates="material"
    )
    machinability_overrides: Mapped[list["MaterialMachinability"]] = relationship(
        back_populates="material"
    )


class MaterialAssortment(Base, TimestampMixin):
    __tablename__ = "material_assortment"
    __table_args__ = (
        UniqueConstraint("material_id", "profile", "size_mm", name="uq_assortment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="CASCADE"), index=True
    )
    profile: Mapped[MaterialProfile] = mapped_column(
        SaEnum(MaterialProfile, native_enum=False, length=20)
    )
    size_mm: Mapped[Decimal] = mapped_column(Numeric(8, 3))

    material: Mapped[Material] = relationship(back_populates="assortment")


class MaterialMachinability(Base, TimestampMixin):
    __tablename__ = "material_machinability"
    __table_args__ = (
        UniqueConstraint(
            "material_id", "operation_group", name="uq_material_machinability"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="CASCADE"), index=True
    )
    operation_group: Mapped[str] = mapped_column(String(50), default="ALL")
    machinability_factor: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    k_finish_factor: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), default=None)
    tool_wear_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2), default=None
    )

    material: Mapped[Material] = relationship(back_populates="machinability_overrides")
