from app.core.security import create_access_token, verify_password
from app.domain.dto.user import LoginRequest, TokenDTO
from app.repositories.uow import UnitOfWork


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def login(self, request: LoginRequest) -> TokenDTO:
        user = await self._uow.users.get_by_email(str(request.email))
        if user is None or not verify_password(request.password, user.password_hash):
            raise InvalidCredentialsError
        token = create_access_token(user.id, str(user.role))
        return TokenDTO(access_token=token)
