from fastapi import Body
from fastapi.routing import APIRouter
from jose import JWTError, jwt

from apps.authentication.domain import (
    RefreshAcceessTokenRequest,
    Token,
    TokenCreate,
    TokenDeleteRequest,
)
from apps.authentication.errors import BadCredentials
from apps.authentication.services.crud import TokensCRUD
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.domain import (
    PublicUser,
    User,
    UserCreate,
    UserLoginRequest,
    UsersError,
    UserSignUpRequest,
)
from apps.users.services import UsersCRUD
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", tags=["Authentication"])
async def create_user(
    user_create_schema: UserSignUpRequest = Body(...),
) -> Response[PublicUser]:
    try:
        # TODO: Change the email to unique
        user: User = await UsersCRUD().get_by_email(
            email=user_create_schema.email
        )
        if user:
            raise UsersError(message="User already exist")
    except UsersError:
        user_in_db = UserCreate(
            email=user_create_schema.email,
            username=user_create_schema.username,
            hashed_password=AuthenticationService.get_password_hash(
                user_create_schema.password
            ),
        )
        user, _ = await UsersCRUD().save_user(schema=user_in_db)

    # Create public user model in order to avoid password sharing
    public_user = PublicUser(**user.dict())

    return Response(result=public_user)


async def authenticate_user(user_login_schema: UserLoginRequest = Body(...)):
    user: User = await UsersCRUD().get_by_email(email=user_login_schema.email)

    if not AuthenticationService.verify_password(
        user_login_schema.password, user.hashed_password
    ):
        raise BadCredentials("Invalid password")

    return user


@router.post("/access-token", tags=["Authentication"])
async def get_access_token(
    user_login_schema: UserLoginRequest = Body(...),
) -> Response[Token]:
    user: User = await authenticate_user(user_login_schema)

    access_token = AuthenticationService.create_access_token(
        data={"sub": user.email}
    )
    refresh_token = AuthenticationService.create_refresh_token(
        data={"sub": user.email}
    )

    try:
        await TokensCRUD()._delete(key="email", value=user_login_schema.email)

        token, _ = await TokensCRUD().save(
            TokenCreate(
                email=user_login_schema.email,
                access_token=access_token,
                refresh_token=refresh_token,
            )
        )
    except UsersError:
        token, _ = await TokensCRUD().save(
            TokenCreate(
                email=user_login_schema.email,
                access_token=access_token,
                refresh_token=refresh_token,
            )
        )

    return Response(result=token)


@router.post("/signout", tags=["Authentication"])
async def access_token_delete(token: TokenDeleteRequest = Body(...)) -> None:
    access_token_not_correct = BadCredentials(
        message="Access token is not correct"
    )

    try:
        payload = jwt.decode(
            token.access_token,
            settings.authentication.secret_key,
            algorithms=[settings.authentication.algorithm],
        )

        if not (email := payload.get("sub")):
            raise access_token_not_correct

    except JWTError:
        raise access_token_not_correct

    try:
        instance: Token = await TokensCRUD().get_by_email(email=email)
        await TokensCRUD().delete(instance.id)
    except UsersError:
        raise access_token_not_correct


@router.post("/refresh-access-token", tags=["Authentication"])
async def refresh_access_token(
    token: RefreshAcceessTokenRequest = Body(...),
) -> Response[Token]:
    """Refresh access token."""
    refresh_token_not_correct = BadCredentials(
        message="Access token is not correct"
    )

    try:
        payload = jwt.decode(
            token.refresh_token,
            settings.authentication.refresh_secret_key,
            algorithms=[settings.authentication.algorithm],
        )

        if not (email := payload.get("sub")):
            raise refresh_token_not_correct

    except JWTError:
        raise refresh_token_not_correct

    try:
        instance: Token = await TokensCRUD().get_by_email(email=email)
        refreshed_access_token: Token = await TokensCRUD().\
            refresh_access_token(instance.id)
        # access_token = Token(**refreshed_access_token.dict())
        return Response(result=refreshed_access_token)
    except UsersError:
        raise refresh_token_not_correct
