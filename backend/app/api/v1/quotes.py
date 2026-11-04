from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_current_user, get_uow, require_roles
from app.db.models import User
from app.domain.dto.quote import (
    AnalogueQueryDTO,
    AnalogueRowDTO,
    QuoteCreateDTO,
    QuoteDetailDTO,
    QuoteReadDTO,
)
from app.domain.enums import UserRole
from app.repositories.uow import UnitOfWork
from app.services.calculation_service import CalculationDataError
from app.services.quote_export import build_quote_xlsx
from app.services.quote_service import QuotePermissionError, QuoteService

router = APIRouter(prefix="/quotes", tags=["quotes"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_quote(
    payload: QuoteCreateDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[
        User,
        Depends(require_roles(UserRole.MANAGER, UserRole.TECHNOLOGIST, UserRole.ADMIN)),
    ],
) -> QuoteDetailDTO:
    try:
        return await QuoteService(uow).create(user.id, payload)
    except CalculationDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("")
async def list_quotes(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[QuoteReadDTO]:
    return list(await QuoteService(uow).list_all())


@router.post("/similar")
async def find_similar_quotes(
    payload: AnalogueQueryDTO,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[AnalogueRowDTO]:
    """Метод аналогов: похожие сохранённые КП по шаблону/габариту/ISO."""
    try:
        return list(await QuoteService(uow).find_analogues(payload))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("/{quote_id}")
async def get_quote(
    quote_id: int,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> QuoteDetailDTO:
    quote = await QuoteService(uow).get(quote_id)
    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Расчёт не найден"
        )
    return quote


@router.get("/{quote_id}/export.xlsx")
async def export_quote_xlsx(
    quote_id: int,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    quote = await QuoteService(uow).get(quote_id)
    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Расчёт не найден"
        )
    content = build_quote_xlsx(quote)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="quote_{quote_id}.xlsx"'
        },
    )


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: int,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    try:
        deleted = await QuoteService(uow).delete(
            quote_id, user.id, user.role == UserRole.ADMIN
        )
    except QuotePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Удалять можно только свои расчёты (или все — для ADMIN)",
        ) from exc
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Расчёт не найден"
        )
