from fastapi import Body, Depends

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.errors import InvalidCredentials
from apps.authentication.services.security import AuthenticationService
from apps.users.domain import User
from apps.users.errors import UserNotFound
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def auth_user(
    user_login_schema: UserLoginRequest = Body(...),
    session=Depends(get_session),
) -> User:
    async with atomic(session):
        try:
            user: User = await AuthenticationService(
                session
            ).authenticate_user(user_login_schema)

        except UserNotFound:
            raise InvalidCredentials(email=user_login_schema.email)

        return user
