from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_uow
from app.db.models import User
from app.domain.dto.user import LoginRequest, TokenDTO, UserRead
from app.repositories.uow import UnitOfWork
from app.services.auth_service import AuthService, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    payload: LoginRequest,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TokenDTO:
    try:
        return await AuthService(uow).login(payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        ) from exc


@router.get("/me")
async def read_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    return UserRead.model_validate(current_user)
