from decimal import Decimal

from sqlalchemy import Boolean, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class ToolBasket(Base, TimestampMixin):
    __tablename__ = "tool_baskets"
    __table_args__ = (
        Index(
            "uq_tool_basket",
            "operation_group",
            "material_iso_group",
            text("coalesce(diameter_from_mm, -1)"),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_group: Mapped[str] = mapped_column(String(50))
    material_iso_group: Mapped[str] = mapped_column(String(1))
    tool_set_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tool_life_min: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    regrindable: Mapped[bool] = mapped_column(Boolean, default=False)
    diameter_from_mm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), default=None
    )
    diameter_to_mm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), default=None)
