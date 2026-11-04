from collections.abc import Sequence

from pydantic import ValidationError

from app.db.models import Quote
from app.domain.dto.calculation import (
    CalculateRequestDTO,
    CalculationResultDTO,
    T1Template,
    T2Template,
    T3Template,
)
from app.domain.dto.quote import (
    TURNED_TEMPLATES,
    AnalogueQueryDTO,
    AnalogueRowDTO,
    QuoteCreateDTO,
    QuoteDetailDTO,
    QuoteReadDTO,
)
from app.repositories.uow import UnitOfWork
from app.services.calculation_service import CalculationService


class QuotePermissionError(Exception):
    pass


def _bbox_mm(request: CalculateRequestDTO) -> tuple[float, ...]:
    """Габарит аналога: токарные → (Ømax, длина), коробки → (L, W, H)."""
    template = request.base_template
    if isinstance(template, T1Template):
        steps = [(s.diameter, s.length) for s in template.dimensions.steps]
    elif isinstance(template, T2Template):
        steps = [(s.diameter, s.length) for s in template.dimensions.outer_steps]
    elif isinstance(template, T3Template):
        return (template.dimensions.outer_diameter, template.dimensions.thickness)
    else:
        dims = template.dimensions
        return (dims.length, dims.width, dims.height)
    return (max(d for d, _ in steps), sum(length for _, length in steps))


def _to_detail(quote: Quote) -> QuoteDetailDTO:
    return QuoteDetailDTO(
        id=quote.id,
        name=quote.name,
        project_id=quote.project_id,
        batch_size=quote.batch_size,
        material_id=quote.material_id,
        price_per_part=quote.price_per_part,
        batch_total_price=quote.batch_total_price,
        author_email=quote.author.email,
        created_at=quote.created_at,
        request=CalculateRequestDTO.model_validate(quote.request_snapshot),
        result=CalculationResultDTO.model_validate(quote.result_snapshot),
    )


def _to_read(quote: Quote) -> QuoteReadDTO:
    return QuoteReadDTO(
        id=quote.id,
        name=quote.name,
        project_id=quote.project_id,
        batch_size=quote.batch_size,
        material_id=quote.material_id,
        price_per_part=quote.price_per_part,
        batch_total_price=quote.batch_total_price,
        author_email=quote.author.email,
        created_at=quote.created_at,
    )


class QuoteService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create(self, author_id: int, dto: QuoteCreateDTO) -> QuoteDetailDTO:
        result = await CalculationService(self._uow).calculate(dto.request)
        quote = Quote(
            name=dto.name,
            project_id=str(dto.request.project_id),
            author_id=author_id,
            material_id=dto.material_id,
            batch_size=dto.request.batch_size,
            price_per_part=result.price_per_part,
            batch_total_price=result.batch_total_price,
            request_snapshot=dto.request.model_dump(mode="json"),
            result_snapshot=result.model_dump(mode="json"),
        )
        self._uow.quotes.add(quote)
        await self._uow.commit()
        fetched = await self._uow.quotes.get_with_author(quote.id)
        assert fetched is not None
        return _to_detail(fetched)

    async def list_all(self) -> Sequence[QuoteReadDTO]:
        return [_to_read(quote) for quote in await self._uow.quotes.list_all()]

    async def get(self, quote_id: int) -> QuoteDetailDTO | None:
        quote = await self._uow.quotes.get_with_author(quote_id)
        return None if quote is None else _to_detail(quote)

    async def delete(self, quote_id: int, user_id: int, is_admin: bool) -> bool | None:
        quote = await self._uow.quotes.get(quote_id)
        if quote is None:
            return None
        if quote.author_id != user_id and not is_admin:
            raise QuotePermissionError
        await self._uow.quotes.delete(quote)
        await self._uow.commit()
        return True

    async def find_analogues(self, query: AnalogueQueryDTO) -> list[AnalogueRowDTO]:
        """Метод аналогов (Контур А): тот же шаблон + ISO, габарит в допуске.

        Отклонение = max по осям |аналог − запрос| / запрос × 100.
        Сортировка: ближе габарит → свежее КП.
        """
        query_dims = self._query_dims(query)
        quotes = await self._uow.quotes.list_all()
        scored: list[tuple[float, int, Quote]] = []
        for quote in quotes:
            try:
                request = CalculateRequestDTO.model_validate(quote.request_snapshot)
            except ValidationError:
                continue
            if str(request.base_template.type) != query.template_type:
                continue
            if (
                query.iso_group is not None
                and request.material.iso_group != query.iso_group
            ):
                continue
            dims = _bbox_mm(request)
            if len(dims) != len(query_dims):
                continue
            deviation = max(
                abs(have - want) / want * 100.0
                for have, want in zip(dims, query_dims, strict=True)
            )
            if deviation <= query.tolerance_percent:
                scored.append((deviation, -quote.id, quote))
        scored.sort(key=lambda item: (item[0], item[1]))
        return [
            AnalogueRowDTO(
                quote_id=quote.id,
                name=quote.name,
                batch_size=quote.batch_size,
                price_per_part=quote.price_per_part,
                author_email=quote.author.email,
                created_at=quote.created_at,
                deviation_percent=round(deviation, 1),
            )
            for deviation, _, quote in scored[: query.limit]
        ]

    @staticmethod
    def _query_dims(query: AnalogueQueryDTO) -> tuple[float, ...]:
        if query.template_type in TURNED_TEMPLATES:
            if query.d_max_mm is None or query.length_mm is None:
                raise ValueError("Для токарных шаблонов укажите d_max_mm и length_mm")
            return (query.d_max_mm, query.length_mm)
        if query.length_mm is None or query.width_mm is None or query.height_mm is None:
            raise ValueError("Для T4/T5 укажите length_mm, width_mm, height_mm")
        return (query.length_mm, query.width_mm, query.height_mm)
