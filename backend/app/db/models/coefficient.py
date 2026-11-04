from decimal import Decimal

from sqlalchemy import Enum as SaEnum
from sqlalchemy import Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import CoefficientType, CooperationServiceType, PriceUnit


class Coefficient(Base, TimestampMixin):
    __tablename__ = "coefficients"
    __table_args__ = (UniqueConstraint("coef_type", "code", name="uq_coefficient"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    coef_type: Mapped[CoefficientType] = mapped_column(
        SaEnum(CoefficientType, native_enum=False, length=20)
    )
    code: Mapped[str] = mapped_column(String(30))
    multiplier: Mapped[Decimal] = mapped_column(Numeric(5, 3))
    description: Mapped[str | None] = mapped_column(String(200), default=None)


class CooperationService(Base, TimestampMixin):
    __tablename__ = "cooperation_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_type: Mapped[CooperationServiceType] = mapped_column(
        SaEnum(CooperationServiceType, native_enum=False, length=20)
    )
    unit: Mapped[PriceUnit] = mapped_column(
        SaEnum(PriceUnit, native_enum=False, length=10)
    )
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    contractor: Mapped[str | None] = mapped_column(String(100), default=None)
    min_lot_qty: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )
