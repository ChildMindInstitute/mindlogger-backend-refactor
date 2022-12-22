from fastapi import Body, Depends

from apps.authentication.deps import get_current_token
from apps.authentication.domain import InternalToken, Token
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.shared.errors import NotContentError
from apps.users.domain import User, UserLoginRequest


async def get_access_token(
    user_login_schema: UserLoginRequest = Body(...),
) -> Response[Token]:
    """Generate the JWT access token."""

    user: User = await AuthenticationService.authenticate_user(
        user_login_schema
    )

    access_token = AuthenticationService.create_access_token(
        {"sub": str(user.id)}
    )

    return Response(result=Token(access_token=access_token))


async def access_token_delete(
    token: InternalToken = Depends(get_current_token),
):
    """Add token to the blacklist."""

    await AuthenticationService.add_access_token_to_blacklist(token)
    raise NotContentError
