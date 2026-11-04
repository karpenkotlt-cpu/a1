import asyncio
import sys

from app.core.security import hash_password
from app.db.models import User
from app.db.models.user import UserRole
from app.db.session import session_factory


async def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python -m scripts.create_user EMAIL PASSWORD ROLE")
    email, password, role = sys.argv[1], sys.argv[2], sys.argv[3]
    async with session_factory() as session:
        session.add(
            User(
                email=email,
                full_name=email,
                password_hash=hash_password(password),
                role=UserRole(role),
            )
        )
        await session.commit()
    print(f"User {email} created with role {role}")


if __name__ == "__main__":
    asyncio.run(main())
