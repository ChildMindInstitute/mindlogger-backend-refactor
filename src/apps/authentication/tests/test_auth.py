import datetime
import uuid
from unittest import mock

from jose import jwt

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import RefreshAccessTokenRequest, TokenPayload
from apps.authentication.router import router as auth_router
from apps.authentication.services import AuthenticationService
from apps.authentication.tests.factories import UserLogoutRequestFactory
from apps.shared.test import BaseTest
from apps.users.domain import User, UserCreate, UserCreateRequest
from apps.users.router import router as user_router
from config import settings

TEST_PASSWORD = "Test1234!"


class TestAuthentication(BaseTest):
    user_create_url = user_router.url_path_for("user_create")
    get_token_url = auth_router.url_path_for("get_token")
    delete_token_url = auth_router.url_path_for("delete_access_token")
    refresh_access_token_url = auth_router.url_path_for("refresh_access_token")

    create_request_user = UserCreateRequest(
        email="tom2@mindlogger.com",
        first_name="Tom",
        last_name="Isaak",
        password=TEST_PASSWORD,
    )
    create_request_logout_user = UserLogoutRequestFactory.build()

    async def test_get_token(self, session, client, user):
        response = await client.post(
            url=self.get_token_url,
            data=dict(email=user.email_encrypted, password=TEST_PASSWORD),
        )
        assert response.status_code == 200
        data = response.json()["result"]
        assert set(data.keys()) == {"user", "token"}
        assert data["user"]["id"] == str(user.id)

    async def test_delete_access_token(self, client, user):
        client.login(user)
        response = await client.post(url=self.delete_token_url)
        assert response.status_code == 200

    async def test_refresh_access_token(self, client, user):
        refresh_access_token_request = RefreshAccessTokenRequest(
            refresh_token=AuthenticationService.create_refresh_token(
                {
                    "sub": str(user.id),
                    "jti": str(uuid.uuid4()),
                }
            )
        )
        response = await client.post(url=self.refresh_access_token_url, data=refresh_access_token_request.dict())
        assert response.status_code == 200

    async def test_login_and_logout_device(self, client, user):
        device_id = str(uuid.uuid4())

        response = await client.post(
            url=self.get_token_url,
            data=dict(device_id=device_id, email=user.email_encrypted, password=TEST_PASSWORD),
        )
        assert response.status_code == 200

        client.login(user)

        response = await client.post(
            url=self.delete_token_url,
            data=dict(device_id=device_id),
        )

        assert response.status_code == 200

    async def _request_refresh_token(self, client, token) -> tuple[int, str | None]:
        response = await client.post(url=self.refresh_access_token_url, data={"refresh_token": token})
        if response.status_code == 200:
            result = response.json()["result"]
            return response.status_code, result["refreshToken"]

        return response.status_code, None

    async def test_refresh_token_key_transition(self, client, tom: User, tom_create: UserCreate):
        token_key = settings.authentication.refresh_token.secret_key

        login_request_user: UserLoginRequest = UserLoginRequest(email=tom_create.email, password=tom_create.password)
        response = await client.post(
            url=self.get_token_url,
            data=login_request_user.dict(),
        )
        assert response.status_code == 200
        result = response.json()["result"]
        refresh_token = result["token"]["refreshToken"]
        payload = jwt.decode(
            refresh_token,
            token_key,
            algorithms=[settings.authentication.algorithm],
        )
        token_data = TokenPayload(**payload)

        new_token_key = "new token key"
        transition_expire_date = datetime.date.today() + datetime.timedelta(days=1)

        # refresh access token, check refresh token not changed
        _status_code, _token = await self._request_refresh_token(client, refresh_token)
        assert response.status_code == 200
        assert _token == refresh_token

        with mock.patch("config.settings.authentication.refresh_token") as token_settings_mock:
            token_settings_mock.secret_key = new_token_key
            token_settings_mock.transition_expire_date = transition_expire_date
            token_settings_mock.expiration = 540

            # test key changed, old token is not valid
            _status_code, _ = await self._request_refresh_token(client, refresh_token)
            assert _status_code == 400

            token_settings_mock.transition_key = token_key

            # check transition expire date
            with mock.patch("apps.authentication.api.auth.datetime") as date_mock:
                date_mock.utcnow().date.return_value = transition_expire_date + datetime.timedelta(days=1)
                _status_code, _ = await self._request_refresh_token(client, refresh_token)
                assert _status_code == 400

            # test transition token key with old token
            _status_code, new_refresh_token = await self._request_refresh_token(client, refresh_token)
            assert _status_code == 200
            assert new_refresh_token
            assert new_refresh_token != refresh_token
            # check expiration date copied from prev token
            payload = jwt.decode(
                new_refresh_token,
                new_token_key,
                algorithms=[settings.authentication.algorithm],
            )
            _token_data = TokenPayload(**payload)
            assert _token_data.exp == token_data.exp

            # check new token is invalid for prev key
            token_settings_mock.secret_key = token_key
            _status_code, _ = await self._request_refresh_token(client, new_token_key)
            assert _status_code == 400
            token_settings_mock.secret_key = new_token_key

            # check new token works
            _status_code, _token = await self._request_refresh_token(client, new_refresh_token)
            assert _status_code == 200
            assert _token == new_refresh_token

            # check old token blacklisted
            _status_code, _ = await self._request_refresh_token(client, refresh_token)
            assert _status_code == 401
