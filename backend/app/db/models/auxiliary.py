from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class AuxiliaryOperation(Base, TimestampMixin):
    __tablename__ = "auxiliary_operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    fixed_time_min: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    rate_per_min: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
