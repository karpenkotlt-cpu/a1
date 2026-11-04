from sqlalchemy import select

from app.db.models import User
from app.repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalars().one_or_none()
