import uuid
from typing import cast

import pytest
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.websockets import WebSocket
from jose import JWTError
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.deps import get_current_token, get_current_user, get_current_user_for_ws, openapi_auth
from apps.authentication.domain.token import InternalToken, JWTClaim
from apps.authentication.domain.token.internal import TokenPurpose
from apps.authentication.errors import AuthenticationError, InvalidCredentials
from apps.authentication.services import AuthenticationService
from apps.authentication.services.core import TokensService
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import User
from apps.users.errors import UserNotFound
from config import settings

TEST_PASSWORD = "Test1234!"
RJTI = str(uuid.uuid4())


@pytest.fixture
def token_blacklist_service(session: AsyncSession) -> TokensService:
    return TokensService(session)


@pytest.fixture
def auth_service(session: AsyncSession) -> AuthenticationService:
    return AuthenticationService(session)


@pytest.fixture
def access_token(user: User, auth_service: AuthenticationService) -> str:
    data = {JWTClaim.sub: str(user.id), JWTClaim.rjti: RJTI}
    return auth_service.create_access_token(data)


@pytest.fixture
def refresh_token(user: User, auth_service: AuthenticationService) -> str:
    data = {JWTClaim.sub: str(user.id), JWTClaim.rjti: RJTI}
    return auth_service.create_refresh_token(data)


@pytest.fixture
def access_token_internal(access_token: str, auth_service: AuthenticationService) -> InternalToken:
    payload = auth_service.extract_token_payload(access_token, settings.authentication.access_token.secret_key)
    return InternalToken(payload=payload)


@pytest.fixture
def refresh_token_internal(refresh_token: str, auth_service: AuthenticationService) -> InternalToken:
    payload = auth_service.extract_token_payload(refresh_token, settings.authentication.refresh_token.secret_key)
    return InternalToken(payload=payload)


@pytest.fixture
def mock_ws(mocker: MockerFixture):
    mock = mocker.MagicMock(spec="fastapi.websockets.WebSocket")
    mock.headers = {}
    return mock


async def test_get_current_user_for_ws__no_protocol_header(session: AsyncSession, mock_ws: WebSocket):
    with pytest.raises(HTTPException):
        await get_current_user_for_ws(mock_ws, session=session)


async def test_get_current_user_for_ws__not_valid_token_type(session: AsyncSession, mock_ws: WebSocket):
    not_valid_token_type = "NotValid"
    mock_ws.headers["sec-websocket-protocol"] = f"{not_valid_token_type}|token"  # type: ignore[index]
    with pytest.raises(HTTPException):
        await get_current_user_for_ws(mock_ws, session=session)


async def test_get_current_user_for_ws__token_is_revoked(
    auth_service: AuthenticationService,
    access_token: str,
    access_token_internal: InternalToken,
    session: AsyncSession,
    mock_ws: WebSocket,
):
    await auth_service.revoke_token(access_token_internal, TokenPurpose.ACCESS)
    assert await auth_service.is_revoked(access_token_internal)
    mock_ws.headers["sec-websocket-protocol"] = f"{settings.authentication.token_type}|{access_token}"  # type: ignore[index]
    with pytest.raises(AuthenticationError):
        await get_current_user_for_ws(mock_ws, session=session)


async def test_get_current_user_for_ws__expired_time_is_less_than_now(
    auth_service: AuthenticationService,
    user: User,
    session: AsyncSession,
    mock_ws: WebSocket,
):
    data = {JWTClaim.sub: str(user.id), JWTClaim.rjti: RJTI}
    settings.authentication.access_token.expiration = 0
    access_token = auth_service.create_access_token(data)
    mock_ws.headers["sec-websocket-protocol"] = f"{settings.authentication.token_type}|{access_token}"  # type: ignore[index]
    with pytest.raises(AuthenticationError):
        await get_current_user_for_ws(mock_ws, session=session)
    settings.authentication.access_token.expiration = 30


async def test_get_current_user_for_ws__internal_error(
    session: AsyncSession, mock_ws: WebSocket, mocker: MockerFixture, access_token: str
):
    mocker.patch("jose.jwt.decode", side_effect=JWTError())
    mock_ws.headers["sec-websocket-protocol"] = f"{settings.authentication.token_type}|{access_token}"  # type: ignore[index]
    with pytest.raises(AuthenticationError):
        await get_current_user_for_ws(mock_ws, session=session)


async def test_get_current_user_for_ws(user: User, access_token: str, session: AsyncSession, mock_ws: WebSocket):
    mock_ws.headers["sec-websocket-protocol"] = f"{settings.authentication.token_type}|{access_token}"  # type: ignore[index]
    act = await get_current_user_for_ws(mock_ws, session=session)
    assert act.id == user.id


async def test_get_current_user(faketime, session: AsyncSession, access_token_internal: InternalToken, user: User):
    current_user = await get_current_user(token=access_token_internal, session=session)
    assert current_user.id == user.id
    crud = UsersCRUD(session)
    user_db = await crud._get("id", user.id)
    user_db = cast(UserSchema, user_db)
    assert user_db.last_seen_at == faketime.current_utc


async def test_get_current_user__token_is_revoked(
    session: AsyncSession, access_token_internal: InternalToken, user: User, auth_service: AuthenticationService
):
    await auth_service.revoke_token(access_token_internal, TokenPurpose.ACCESS)
    assert await auth_service.is_revoked(access_token_internal)
    with pytest.raises(AuthenticationError):
        await get_current_user(token=access_token_internal, session=session)


async def test_get_current_access_token(access_token: str, user: User):
    coro = get_current_token()
    internal_token = await coro(token=access_token)
    assert internal_token.payload.sub == user.id
    assert internal_token.raw_token == access_token


async def test_get_current_refresh_token(refresh_token: str, user: User):
    coro = get_current_token(TokenPurpose.REFRESH)
    internal_token = await coro(token=refresh_token)
    assert internal_token.payload.sub == user.id
    assert internal_token.raw_token == refresh_token


async def test_get_current_access_token__internal_error(access_token: str, mocker: MockerFixture):
    mocker.patch("jose.jwt.decode", side_effect=JWTError())
    coro = get_current_token()
    with pytest.raises(AuthenticationError):
        await coro(token=access_token)


async def test_get_current_access_token__expired_time_is_less_than_now(auth_service: AuthenticationService, user: User):
    data = {JWTClaim.sub: str(user.id), JWTClaim.rjti: RJTI}
    settings.authentication.access_token.expiration = 0
    access_token = auth_service.create_access_token(data)
    coro = get_current_token()
    with pytest.raises(AuthenticationError):
        await coro(token=access_token)
    settings.authentication.access_token.expiration = 30


async def test_openapi_auth(session: AsyncSession, user: User):
    form = OAuth2PasswordRequestForm(username=user.email_encrypted, password=TEST_PASSWORD)  # type: ignore[arg-type]
    data = await openapi_auth(form_data=form, session=session)
    assert data["token_type"] == settings.authentication.token_type


async def test_openapi_auth__user_not_found(session: AsyncSession):
    form = OAuth2PasswordRequestForm(username="notexisting@example.com", password=TEST_PASSWORD)
    with pytest.raises(UserNotFound):
        await openapi_auth(form_data=form, session=session)


async def test_openapi_auth__not_valid_password(session: AsyncSession, user: User):
    form = OAuth2PasswordRequestForm(username=user.email_encrypted, password="not_valid_pass")  # type: ignore[arg-type]
    with pytest.raises(InvalidCredentials):
        await openapi_auth(form_data=form, session=session)
