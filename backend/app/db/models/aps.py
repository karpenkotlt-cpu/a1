from datetime import datetime
from decimal import Decimal

from sqlalchemy import Computed, DateTime, Integer, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class ShopCapacityLoad(Base):
    __tablename__ = "shop_capacity_load"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_center_group: Mapped[str] = mapped_column(String(50), unique=True)
    horizon_days: Mapped[int] = mapped_column(
        Integer, default=30, server_default=text("30")
    )
    total_fund_minutes: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    scheduled_minutes: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    utilization_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        Computed("scheduled_minutes / NULLIF(total_fund_minutes, 0)", persisted=True),
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
