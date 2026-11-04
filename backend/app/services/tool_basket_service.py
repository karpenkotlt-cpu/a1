from collections.abc import Sequence

from app.domain.dto.tool_basket import (
    ToolBasketReadDTO,
    ToolBasketUpdateDTO,
)
from app.repositories.uow import UnitOfWork


class ToolBasketService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list_all(self) -> Sequence[ToolBasketReadDTO]:
        baskets = await self._uow.tool_baskets.list_all()
        return [ToolBasketReadDTO.model_validate(basket) for basket in baskets]

    async def update(
        self, basket_id: int, dto: ToolBasketUpdateDTO
    ) -> ToolBasketReadDTO | None:
        basket = await self._uow.tool_baskets.get(basket_id)
        if basket is None:
            return None
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(basket, field, value)
        await self._uow.commit()
        await self._uow.session.refresh(basket)
        return ToolBasketReadDTO.model_validate(basket)
