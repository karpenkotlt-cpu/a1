from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SaEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.enums import UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[UserRole] = mapped_column(
        SaEnum(UserRole, native_enum=False, length=20)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
