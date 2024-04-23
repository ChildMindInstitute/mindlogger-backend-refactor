import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import WebSocket
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.domain.token import InternalToken, JWTClaim
from apps.authentication.services import AuthenticationService
from apps.authentication.services.core import TokensService
from apps.users.domain import User
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
def mock_ws(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock(spec=WebSocket)
    mock.headers = {}
    return mock
