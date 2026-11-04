from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.user import User


class Quote(Base, TimestampMixin):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    project_id: Mapped[str] = mapped_column(String(36))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    material_id: Mapped[int | None] = mapped_column(
        ForeignKey("materials.id", ondelete="SET NULL"), default=None
    )
    batch_size: Mapped[int] = mapped_column(Integer)
    price_per_part: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    batch_total_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    request_snapshot: Mapped[dict[str, object]] = mapped_column(JSON)
    result_snapshot: Mapped[dict[str, object]] = mapped_column(JSON)

    author: Mapped[User] = relationship()
