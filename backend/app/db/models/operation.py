from decimal import Decimal

from sqlalchemy import Enum as SaEnum
from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import OperationType


class Operation(Base, TimestampMixin):
    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    operation_type: Mapped[OperationType] = mapped_column(
        SaEnum(OperationType, native_enum=False, length=20)
    )
    work_center_group: Mapped[str] = mapped_column(String(50), index=True)
    min_tool_diameter_mm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), default=None
    )
    setup_time_base_min: Mapped[Decimal] = mapped_column(
        Numeric(6, 1), default=Decimal("0.0")
    )

    performance_rates: Mapped[list["OperationPerformanceRate"]] = relationship(
        back_populates="operation"
    )


class OperationPerformanceRate(Base, TimestampMixin):
    __tablename__ = "operation_performance_rates"
    __table_args__ = (
        UniqueConstraint(
            "operation_id", "material_iso_group", name="uq_operation_rate"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), index=True
    )
    material_iso_group: Mapped[str] = mapped_column(String(1))
    q_rough_cm3_min: Mapped[Decimal] = mapped_column(Numeric(8, 3))
    s_finish_dm2_min: Mapped[Decimal] = mapped_column(Numeric(8, 3))

    operation: Mapped[Operation] = relationship(back_populates="performance_rates")
