from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Quote
from app.repositories.base import Repository


class QuoteRepository(Repository[Quote]):
    model = Quote

    async def list_all(self) -> Sequence[Quote]:
        result = await self.session.execute(
            select(Quote).options(selectinload(Quote.author)).order_by(Quote.id.desc())
        )
        return result.scalars().all()

    async def get_with_author(self, quote_id: int) -> Quote | None:
        result = await self.session.execute(
            select(Quote)
            .options(selectinload(Quote.author))
            .where(Quote.id == quote_id)
        )
        return result.scalars().one_or_none()
