from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class DrillingRate(Base, TimestampMixin):
    __tablename__ = "drilling_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    diameter_from_mm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    diameter_to_mm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    carbide_feed_mm_min: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    hss_feed_mm_min: Mapped[Decimal] = mapped_column(Numeric(6, 1))
