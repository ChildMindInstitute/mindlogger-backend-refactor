import datetime
import http
import uuid
from unittest import mock

import jwt
import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import RefreshAccessTokenRequest, TokenPayload
from apps.authentication.errors import AuthenticationError, InvalidCredentials, InvalidRefreshToken
from apps.authentication.router import router as auth_router
from apps.authentication.services import AuthenticationService
from apps.authentication.tests.factories import UserLogoutRequestFactory
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User, UserCreate, UserCreateRequest
from config import settings

TEST_PASSWORD = "Test1234!"


class TestAuthentication(BaseTest):
    get_token_url = auth_router.url_path_for("get_token")
    delete_token_url = auth_router.url_path_for("delete_access_token")
    refresh_access_token_url = auth_router.url_path_for("refresh_access_token")
    delete_refresh_token_url = auth_router.url_path_for("delete_refresh_token")

    create_request_user = UserCreateRequest(
        email="tom2@mindlogger.com",
        first_name="Tom",
        last_name="Isaak",
        password=TEST_PASSWORD,
    )
    create_request_logout_user = UserLogoutRequestFactory.build()

    async def test_get_token(self, client: TestClient, user: User):
        response = await client.post(
            url=self.get_token_url,
            data=dict(email=user.email_encrypted, password=TEST_PASSWORD, deviceId="test#device"),
        )
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]
        assert set(data.keys()) == {"user", "token"}
        assert data["user"]["id"] == str(user.id)

    async def test_delete_access_token(self, client: TestClient, user: User):
        client.login(user)
        response = await client.post(url=self.delete_token_url)
        assert response.status_code == http.HTTPStatus.OK

    async def test_refresh_access_token(self, client: TestClient, user: User):
        refresh_access_token_request = RefreshAccessTokenRequest(
            refresh_token=AuthenticationService.create_refresh_token(
                {
                    "sub": str(user.id),
                    "jti": str(uuid.uuid4()),
                }
            )
        )
        response = await client.post(url=self.refresh_access_token_url, data=refresh_access_token_request.dict())
        assert response.status_code == http.HTTPStatus.OK

    async def test_login_and_logout_device(self, client: TestClient, user: User):
        device_id = str(uuid.uuid4())

        response = await client.post(
            url=self.get_token_url,
            data=dict(device_id=device_id, email=user.email_encrypted, password=TEST_PASSWORD),
        )
        assert response.status_code == http.HTTPStatus.OK

        client.login(user)

        response = await client.post(
            url=self.delete_token_url,
            data=dict(device_id=device_id),
        )

        assert response.status_code == http.HTTPStatus.OK

    async def _request_refresh_token(self, client: TestClient, token: str) -> tuple[int, str | None]:
        response = await client.post(url=self.refresh_access_token_url, data={"refresh_token": token})
        if response.status_code == http.HTTPStatus.OK:
            result = response.json()["result"]
            return response.status_code, result["refreshToken"]

        return response.status_code, None

    async def test_refresh_token_key_transition(self, client, tom: User, tom_create: UserCreate, mocker: MockerFixture):
        token_key = settings.authentication.refresh_token.secret_key

        login_request_user: UserLoginRequest = UserLoginRequest(email=tom_create.email, password=tom_create.password)
        response = await client.post(
            url=self.get_token_url,
            data=login_request_user.dict(),
        )
        assert response.status_code == http.HTTPStatus.OK
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
        assert response.status_code == http.HTTPStatus.OK
        assert _token == refresh_token

        with mock.patch("config.settings.authentication.refresh_token") as token_settings_mock:
            token_settings_mock.secret_key = new_token_key
            token_settings_mock.transition_expire_date = transition_expire_date
            token_settings_mock.expiration = 540

            # test key changed, old token is not valid
            _status_code, _ = await self._request_refresh_token(client, refresh_token)
            assert _status_code == http.HTTPStatus.BAD_REQUEST

            token_settings_mock.transition_key = token_key

            # check transition expire date
            with mock.patch("apps.authentication.api.auth.datetime") as date_mock:
                date_mock.utcnow().date.return_value = transition_expire_date + datetime.timedelta(days=1)
                _status_code, _ = await self._request_refresh_token(client, refresh_token)
                assert _status_code == http.HTTPStatus.BAD_REQUEST

            # test transition token key with old token
            _status_code, new_refresh_token = await self._request_refresh_token(client, refresh_token)
            assert _status_code == http.HTTPStatus.OK
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
            assert _status_code == http.HTTPStatus.BAD_REQUEST
            token_settings_mock.secret_key = new_token_key

            # check new token works
            _status_code, _token = await self._request_refresh_token(client, new_refresh_token)
            assert _status_code == http.HTTPStatus.OK
            assert _token == new_refresh_token

            # check old token blacklisted
            _status_code, _ = await self._request_refresh_token(client, refresh_token)
            assert _status_code == http.HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize("field_name,value", (("email", "notfound@example.com"), ("password", "1234")))
    async def test_get_token_credentials_are_not_valid(
        self, client: TestClient, user: User, field_name: str, value: str
    ):
        data = dict(email=user.email_encrypted, password=TEST_PASSWORD)
        data[field_name] = value
        resp = await client.post(self.get_token_url, data=data)
        assert resp.status_code == http.HTTPStatus.UNAUTHORIZED
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == InvalidCredentials.message

    async def test_get_token__email_encrypted_updated_if_there_is_no_email(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        email = user.email_encrypted
        updated = await UsersCRUD(session).update_encrypted_email(user, None)  # type: ignore[arg-type]
        assert updated.email_encrypted is None
        data = dict(email=email, password=TEST_PASSWORD)
        resp = await client.post(self.get_token_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert email == (await UsersCRUD(session).get_by_id(user.id)).email_encrypted

    async def test_logout2(self, client: TestClient, user: User):
        resp = await client.post(self.get_token_url, data={"email": user.email_encrypted, "password": TEST_PASSWORD})
        assert resp.status_code == http.HTTPStatus.OK
        refresh_token = resp.json()["result"]["token"]["refreshToken"]
        # To revoke refresh_token need to send it in header
        resp = await client.post(self.delete_refresh_token_url, headers={"Authorization": f"Bearer {refresh_token}"})
        assert resp.status_code == http.HTTPStatus.OK
        resp = await client.post(
            self.refresh_access_token_url,
            data={"refresh_token": refresh_token},
        )
        assert resp.status_code == http.HTTPStatus.UNAUTHORIZED
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AuthenticationError.message

    async def test_logout2_device_removed(self, client: TestClient, user: User, mocker: MockerFixture):
        device_id = "device_id"
        resp = await client.post(
            self.get_token_url, data={"email": user.email_encrypted, "password": TEST_PASSWORD, "device_id": device_id}
        )
        assert resp.status_code == http.HTTPStatus.OK
        refresh_token = resp.json()["result"]["token"]["refreshToken"]
        mock_ = mocker.patch("apps.users.services.user_device.UserDeviceService.remove_device")
        resp = await client.post(
            self.delete_refresh_token_url,
            headers={"Authorization": f"Bearer {refresh_token}"},
            data={"device_id": device_id},
        )
        assert resp.status_code == http.HTTPStatus.OK
        mock_.assert_awaited_once_with(device_id)

    async def test_refresh_access_token__refresh_token_is_expired(self, client: TestClient, user: User):
        settings.authentication.refresh_token.expiration = -1
        resp = await client.post(self.get_token_url, data={"email": user.email_encrypted, "password": TEST_PASSWORD})
        assert resp.status_code == http.HTTPStatus.OK
        refresh_token = resp.json()["result"]["token"]["refreshToken"]
        resp = await client.post(self.refresh_access_token_url, data={"refresh_token": refresh_token})
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == InvalidRefreshToken.message
        settings.authentication.refresh_token.expiration = 540
