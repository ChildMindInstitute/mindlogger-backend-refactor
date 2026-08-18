import datetime
import http
import uuid
from unittest import mock

import jwt
import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import Message
from starlette.websockets import WebSocket

from apps.audit import EventAction, EventOutcome
from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import RefreshAccessTokenRequest, TokenPayload
from apps.authentication.errors import (
    AuthenticationError,
    InvalidCredentials,
    InvalidRefreshToken,
    SessionTokenInvalidError,
)
from apps.authentication.router import router as auth_router
from apps.authentication.services import AuthenticationService
from apps.authentication.tests.factories import UserLogoutRequestFactory
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User, UserCreate, UserCreateRequest
from config import settings
from infrastructure.http.exceptions import session_token_invalid_error_handler

TEST_PASSWORD = "Test12345!"


class TestAuthentication(BaseTest):
    get_token_url = auth_router.url_path_for("get_token")
    delete_token_url = auth_router.url_path_for("delete_access_token")
    refresh_access_token_url = auth_router.url_path_for("refresh_access_token")
    delete_refresh_token_url = auth_router.url_path_for("delete_refresh_token")

    create_request_user = UserCreateRequest(
        email="tom2@gettingcurious.com",
        first_name="Tom",
        last_name="Isaak",
        password=TEST_PASSWORD,
    )
    create_request_logout_user = UserLogoutRequestFactory.build()

    async def test_get_token(self, client: TestClient, user: User, mocker: MockerFixture):
        audit_log = mocker.patch("apps.authentication.api.auth.log")
        response = await client.post(
            url=self.get_token_url,
            data=dict(email=user.email_encrypted, password=TEST_PASSWORD, deviceId="test#device"),
        )
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == user.id
        assert event.event_action == EventAction.USER_SESSION_LOGIN
        assert event.event_outcome == EventOutcome.SUCCESS
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]
        assert set(data.keys()) == {"user", "token"}
        assert data["user"]["id"] == str(user.id)

    async def test_malformed_token(self, client: TestClient, mocker: MockerFixture):
        audit_log = mocker.patch("infrastructure.http.exceptions.log")
        resp = await client.post(
            self.delete_token_url,
            headers={"Authorization": f"{settings.authentication.token_type} not-a-jwt"},
        )
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id is None
        assert event.event_action == EventAction.USER_SESSION_INVALID
        assert event.event_outcome == EventOutcome.FAILURE
        assert resp.status_code == http.HTTPStatus.UNAUTHORIZED
        assert resp.json()["result"][0]["message"] == SessionTokenInvalidError.message

    async def test_expired_token(self, client: TestClient, user: User, mocker: MockerFixture):
        mocker.patch.object(settings.authentication.access_token, "expiration", -1)
        client.login(user)
        audit_log = mocker.patch("infrastructure.http.exceptions.log")
        resp = await client.post(self.delete_token_url)
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == user.id
        assert event.event_action == EventAction.USER_SESSION_INVALID
        assert event.event_outcome == EventOutcome.FAILURE
        assert resp.status_code == http.HTTPStatus.UNAUTHORIZED
        assert resp.json()["result"][0]["message"] == SessionTokenInvalidError.message

    async def test_revoked_token(self, client: TestClient, user: User, mocker: MockerFixture):
        client.login(user)
        logout_resp = await client.post(self.delete_token_url)
        assert logout_resp.status_code == http.HTTPStatus.OK
        audit_log = mocker.patch("infrastructure.http.exceptions.log")
        resp = await client.post(self.delete_token_url)
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == user.id
        assert event.event_action == EventAction.USER_SESSION_INVALID
        assert event.event_outcome == EventOutcome.FAILURE
        assert resp.status_code == http.HTTPStatus.UNAUTHORIZED
        assert resp.json()["result"][0]["message"] == SessionTokenInvalidError.message

    async def test_user_not_found(self, client: TestClient, mocker: MockerFixture):
        unknown_user_id = uuid.uuid4()
        client.login(unknown_user_id)
        audit_log = mocker.patch("infrastructure.http.exceptions.log")
        resp = await client.post(self.delete_token_url)
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == unknown_user_id
        assert event.event_action == EventAction.USER_SESSION_INVALID
        assert event.event_outcome == EventOutcome.FAILURE
        assert resp.status_code == http.HTTPStatus.UNAUTHORIZED
        assert resp.json()["result"][0]["message"] == SessionTokenInvalidError.message

    async def test_ws_session_invalid_audit_event(self, mocker: MockerFixture):
        """A `SessionTokenInvalidError` raised from a WebSocket connection (e.g. `/ws/alerts`) must

        log the `user:session:invalid` audit event without crashing. `http_audit_fields` used to
        read the HTTP-only `request.method`, which a `WebSocket` lacks.
        """
        audit_log = mocker.patch("infrastructure.http.exceptions.log")
        user_id = uuid.uuid4()

        async def receive() -> Message:
            return {"type": "websocket.connect"}

        async def send(message: Message) -> None:
            return None

        websocket = WebSocket(
            {
                "type": "websocket",
                "scheme": "ws",
                "server": ("test.com", 80),
                "path": "/ws/alerts",
                "query_string": b"",
                "root_path": "",
                "headers": [(b"host", b"test.com"), (b"user-agent", b"pytest-ws-client")],
                "client": ("10.1.2.3", 54321),
            },
            receive=receive,
            send=send,
        )
        error = SessionTokenInvalidError(user_id=user_id)

        resp = await session_token_invalid_error_handler(websocket, error)

        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.event_action == EventAction.USER_SESSION_INVALID
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.user_id == user_id
        assert event.http_request_method is None  # WebSocket has no HTTP method
        assert event.url_path == "/ws/alerts"
        assert event.client_ip == "10.1.2.3"
        assert event.user_agent == "pytest-ws-client"
        assert resp.status_code == http.HTTPStatus.UNAUTHORIZED

    async def test_delete_access_token(self, client: TestClient, user: User, mocker: MockerFixture):
        audit_log = mocker.patch("apps.authentication.api.auth.log")
        client.login(user)
        response = await client.post(url=self.delete_token_url)
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == user.id
        assert event.event_action == EventAction.USER_SESSION_LOGOUT
        assert event.event_outcome == EventOutcome.SUCCESS
        assert response.status_code == http.HTTPStatus.OK

    async def test_refresh_access_token(self, client: TestClient, user: User, mocker: MockerFixture):
        audit_log = mocker.patch("apps.authentication.api.auth.log")
        refresh_access_token_request = RefreshAccessTokenRequest(
            refresh_token=AuthenticationService.create_refresh_token(
                {
                    "sub": str(user.id),
                    "jti": str(uuid.uuid4()),
                }
            )
        )
        response = await client.post(url=self.refresh_access_token_url, data=refresh_access_token_request.model_dump())
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == user.id
        assert event.event_action == EventAction.USER_SESSION_REFRESH
        assert event.event_outcome == EventOutcome.SUCCESS
        assert response.status_code == http.HTTPStatus.OK

    async def test_refresh_access_token__propagates_client_claim(
        self, client: TestClient, user: User, mocker: MockerFixture
    ):
        mocker.patch("apps.authentication.api.auth.log")
        refresh_token = AuthenticationService.create_refresh_token(
            {
                "sub": str(user.id),
                "jti": str(uuid.uuid4()),
                "client": "admin",
            }
        )
        response = await client.post(url=self.refresh_access_token_url, data={"refresh_token": refresh_token})
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["refreshToken"] == refresh_token
        access_payload = jwt.decode(
            result["accessToken"],
            settings.authentication.access_token.secret_key,
            algorithms=[settings.authentication.algorithm],
        )
        assert access_payload["client"] == "admin"

    async def test_refresh_access_token__legacy_token_without_client_claim(
        self, client: TestClient, user: User, mocker: MockerFixture
    ):
        mocker.patch("apps.authentication.api.auth.log")
        refresh_token = AuthenticationService.create_refresh_token(
            {
                "sub": str(user.id),
                "jti": str(uuid.uuid4()),
            }
        )
        response = await client.post(url=self.refresh_access_token_url, data={"refresh_token": refresh_token})
        assert response.status_code == http.HTTPStatus.OK
        access_payload = jwt.decode(
            response.json()["result"]["accessToken"],
            settings.authentication.access_token.secret_key,
            algorithms=[settings.authentication.algorithm],
        )
        assert "client" not in access_payload

    async def test_refresh_token_key_transition__preserves_client_claim(
        self, client: TestClient, user: User, mocker: MockerFixture
    ):
        token_key = settings.authentication.refresh_token.secret_key
        refresh_token = AuthenticationService.create_refresh_token(
            {
                "sub": str(user.id),
                "jti": str(uuid.uuid4()),
                "client": "web",
            }
        )
        new_token_key = "new token key"
        transition_expire_date = datetime.datetime.now(datetime.timezone.utc).date() + datetime.timedelta(days=1)

        with mock.patch("config.settings.authentication.refresh_token") as token_settings_mock:
            token_settings_mock.secret_key = new_token_key
            token_settings_mock.transition_key = token_key
            token_settings_mock.transition_expire_date = transition_expire_date
            token_settings_mock.expiration = 540

            _status_code, new_refresh_token = await self._request_refresh_token(client, refresh_token)
            assert _status_code == http.HTTPStatus.OK
            assert new_refresh_token
            assert new_refresh_token != refresh_token
            refresh_payload = jwt.decode(
                new_refresh_token,
                new_token_key,
                algorithms=[settings.authentication.algorithm],
            )
            assert refresh_payload["client"] == "web"

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
            data=login_request_user.model_dump(),
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
        transition_expire_date = datetime.datetime.now(datetime.timezone.utc).date() + datetime.timedelta(days=1)

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
                date_mock.now().date.return_value = transition_expire_date + datetime.timedelta(days=1)
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
        self, client: TestClient, user: User, field_name: str, value: str, mocker: MockerFixture
    ):
        audit_log = mocker.patch("apps.authentication.api.auth.log")
        data = dict(email=user.email_encrypted, password=TEST_PASSWORD)
        data[field_name] = value
        resp = await client.post(self.get_token_url, data=data)
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id is None
        assert event.user_email == data["email"]
        assert event.event_action == EventAction.USER_SESSION_LOGIN
        assert event.event_outcome == EventOutcome.FAILURE
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

    async def test_refresh_access_token__refresh_token_is_expired(
        self, client: TestClient, user: User, mocker: MockerFixture
    ):
        settings.authentication.refresh_token.expiration = -1
        resp = await client.post(self.get_token_url, data={"email": user.email_encrypted, "password": TEST_PASSWORD})
        assert resp.status_code == http.HTTPStatus.OK
        refresh_token = resp.json()["result"]["token"]["refreshToken"]
        audit_log = mocker.patch("apps.authentication.api.auth.log")
        resp = await client.post(self.refresh_access_token_url, data={"refresh_token": refresh_token})
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id is None
        assert event.event_action == EventAction.USER_SESSION_REFRESH
        assert event.event_outcome == EventOutcome.FAILURE
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == InvalidRefreshToken.message
        settings.authentication.refresh_token.expiration = 540


class TestLoginClientClaim(BaseTest):
    """The client claim records which client tokens were issued to, without changing lifetimes."""

    get_token_url = auth_router.url_path_for("get_token")

    @staticmethod
    def _decode_tokens(result: dict) -> tuple[dict, dict]:
        access_payload = jwt.decode(
            result["token"]["accessToken"],
            settings.authentication.access_token.secret_key,
            algorithms=[settings.authentication.algorithm],
        )
        refresh_payload = jwt.decode(
            result["token"]["refreshToken"],
            settings.authentication.refresh_token.secret_key,
            algorithms=[settings.authentication.algorithm],
        )
        return access_payload, refresh_payload

    @staticmethod
    def _assert_expires_in(exp: int, minutes: int, before: datetime.datetime, after: datetime.datetime):
        delta = datetime.timedelta(minutes=minutes)
        assert int((before + delta).timestamp()) <= exp <= int((after + delta).timestamp()) + 1

    @pytest.mark.parametrize("content_source", ("web", "admin", "mobile"))
    async def test_login_embeds_client_claim(self, client: TestClient, user: User, content_source: str):
        before = datetime.datetime.now(datetime.timezone.utc)
        resp = await client.post(
            self.get_token_url,
            data={"email": user.email_encrypted, "password": TEST_PASSWORD},
            headers={"Mindlogger-Content-Source": content_source},
        )
        after = datetime.datetime.now(datetime.timezone.utc)
        assert resp.status_code == http.HTTPStatus.OK
        access_payload, refresh_payload = self._decode_tokens(resp.json()["result"])
        assert access_payload["client"] == content_source
        assert refresh_payload["client"] == content_source
        # web/admin get the short lifetimes; mobile keeps the defaults.
        if content_source in ("web", "admin"):
            expected_access = settings.authentication.access_token.web_admin_expiration
            expected_refresh = settings.authentication.refresh_token.web_admin_expiration
            assert expected_access is not None and expected_refresh is not None
        else:
            expected_access = settings.authentication.access_token.expiration
            expected_refresh = settings.authentication.refresh_token.expiration
        self._assert_expires_in(access_payload["exp"], expected_access, before, after)
        self._assert_expires_in(refresh_payload["exp"], expected_refresh, before, after)

    async def test_login_audit_event_records_client_source(self, client: TestClient, user: User, mocker: MockerFixture):
        audit_log = mocker.patch("apps.authentication.api.auth.log")
        resp = await client.post(
            self.get_token_url,
            data={"email": user.email_encrypted, "password": TEST_PASSWORD},
            headers={"Mindlogger-Content-Source": "admin"},
        )
        assert resp.status_code == http.HTTPStatus.OK
        event = audit_log.call_args[0][0]
        assert event.client_source == "admin"

    async def test_login_audit_event_without_client_source(self, client: TestClient, user: User, mocker: MockerFixture):
        audit_log = mocker.patch("apps.authentication.api.auth.log")
        resp = await client.post(
            self.get_token_url,
            data={"email": user.email_encrypted, "password": TEST_PASSWORD},
        )
        assert resp.status_code == http.HTTPStatus.OK
        event = audit_log.call_args[0][0]
        assert event.client_source is None

    async def test_refresh_audit_event_records_client_source(
        self, client: TestClient, user: User, mocker: MockerFixture
    ):
        audit_log = mocker.patch("apps.authentication.api.auth.log")
        refresh_token = AuthenticationService.create_refresh_token(
            {
                "sub": str(user.id),
                "jti": str(uuid.uuid4()),
                "client": "web",
            }
        )
        resp = await client.post(
            auth_router.url_path_for("refresh_access_token"),
            data={"refresh_token": refresh_token},
            headers={"Mindlogger-Content-Source": "web"},
        )
        assert resp.status_code == http.HTTPStatus.OK
        event = audit_log.call_args[0][0]
        assert event.client_source == "web"

    @pytest.mark.parametrize(
        "headers",
        (None, {"Mindlogger-Content-Source": "invalid-content-source"}),
        ids=("missing-header", "invalid-header"),
    )
    async def test_login_without_client_claim(self, client: TestClient, user: User, headers: dict | None):
        before = datetime.datetime.now(datetime.timezone.utc)
        resp = await client.post(
            self.get_token_url,
            data={"email": user.email_encrypted, "password": TEST_PASSWORD},
            headers=headers,
        )
        after = datetime.datetime.now(datetime.timezone.utc)
        assert resp.status_code == http.HTTPStatus.OK
        access_payload, refresh_payload = self._decode_tokens(resp.json()["result"])
        assert "client" not in access_payload
        assert "client" not in refresh_payload
        # No client claim -> default (mobile) lifetimes.
        self._assert_expires_in(access_payload["exp"], settings.authentication.access_token.expiration, before, after)
        self._assert_expires_in(refresh_payload["exp"], settings.authentication.refresh_token.expiration, before, after)


class TestShortLivedWebAdminTokens(BaseTest):
    """Web/admin clients get shorter token lifetimes when configured; others are unchanged."""

    get_token_url = auth_router.url_path_for("get_token")
    refresh_access_token_url = auth_router.url_path_for("refresh_access_token")

    SHORT_ACCESS = 15
    SHORT_REFRESH = 120

    @pytest.fixture
    def short_lifetimes(self, mocker: MockerFixture):
        mocker.patch.object(settings.authentication.access_token, "web_admin_expiration", self.SHORT_ACCESS)
        mocker.patch.object(settings.authentication.refresh_token, "web_admin_expiration", self.SHORT_REFRESH)

    @staticmethod
    def _decode(token: str, secret: str) -> dict:
        return jwt.decode(token, secret, algorithms=[settings.authentication.algorithm])

    @staticmethod
    def _assert_expires_in(exp: int, minutes: int, before: datetime.datetime, after: datetime.datetime):
        delta = datetime.timedelta(minutes=minutes)
        assert int((before + delta).timestamp()) <= exp <= int((after + delta).timestamp()) + 1

    @pytest.mark.parametrize("content_source", ("web", "admin"))
    async def test_web_admin_get_short_lifetimes(
        self, client: TestClient, user: User, short_lifetimes, content_source: str
    ):
        before = datetime.datetime.now(datetime.timezone.utc)
        resp = await client.post(
            self.get_token_url,
            data={"email": user.email_encrypted, "password": TEST_PASSWORD},
            headers={"Mindlogger-Content-Source": content_source},
        )
        after = datetime.datetime.now(datetime.timezone.utc)
        assert resp.status_code == http.HTTPStatus.OK
        token = resp.json()["result"]["token"]
        access = self._decode(token["accessToken"], settings.authentication.access_token.secret_key)
        refresh = self._decode(token["refreshToken"], settings.authentication.refresh_token.secret_key)
        self._assert_expires_in(access["exp"], self.SHORT_ACCESS, before, after)
        self._assert_expires_in(refresh["exp"], self.SHORT_REFRESH, before, after)

    @pytest.mark.parametrize(
        "headers",
        ({"Mindlogger-Content-Source": "mobile"}, None),
        ids=("mobile", "no-header"),
    )
    async def test_mobile_and_unknown_keep_default_lifetimes(
        self, client: TestClient, user: User, short_lifetimes, headers: dict | None
    ):
        before = datetime.datetime.now(datetime.timezone.utc)
        resp = await client.post(
            self.get_token_url,
            data={"email": user.email_encrypted, "password": TEST_PASSWORD},
            headers=headers,
        )
        after = datetime.datetime.now(datetime.timezone.utc)
        assert resp.status_code == http.HTTPStatus.OK
        token = resp.json()["result"]["token"]
        access = self._decode(token["accessToken"], settings.authentication.access_token.secret_key)
        refresh = self._decode(token["refreshToken"], settings.authentication.refresh_token.secret_key)
        self._assert_expires_in(access["exp"], settings.authentication.access_token.expiration, before, after)
        self._assert_expires_in(refresh["exp"], settings.authentication.refresh_token.expiration, before, after)

    async def test_refresh_preserves_short_access_lifetime(
        self, client: TestClient, user: User, short_lifetimes, mocker: MockerFixture
    ):
        mocker.patch("apps.authentication.api.auth.log")
        login = await client.post(
            self.get_token_url,
            data={"email": user.email_encrypted, "password": TEST_PASSWORD},
            headers={"Mindlogger-Content-Source": "admin"},
        )
        refresh_token = login.json()["result"]["token"]["refreshToken"]

        before = datetime.datetime.now(datetime.timezone.utc)
        resp = await client.post(
            self.refresh_access_token_url,
            data={"refresh_token": refresh_token},
            headers={"Mindlogger-Content-Source": "admin"},
        )
        after = datetime.datetime.now(datetime.timezone.utc)
        assert resp.status_code == http.HTTPStatus.OK
        access = self._decode(resp.json()["result"]["accessToken"], settings.authentication.access_token.secret_key)
        self._assert_expires_in(access["exp"], self.SHORT_ACCESS, before, after)

    async def test_logout_revokes_paired_refresh_token_under_short_lifetimes(
        self, client: TestClient, user: User, short_lifetimes, mocker: MockerFixture
    ):
        mocker.patch("apps.authentication.api.auth.log")
        login = await client.post(
            self.get_token_url,
            data={"email": user.email_encrypted, "password": TEST_PASSWORD},
            headers={"Mindlogger-Content-Source": "admin"},
        )
        token = login.json()["result"]["token"]

        logout = await client.post(
            auth_router.url_path_for("delete_access_token"),
            headers={"Authorization": f"Bearer {token['accessToken']}"},
        )
        assert logout.status_code == http.HTTPStatus.OK

        # Revoking the access token must also revoke its paired refresh token.
        resp = await client.post(
            self.refresh_access_token_url,
            data={"refresh_token": token["refreshToken"]},
        )
        assert resp.status_code == http.HTTPStatus.UNAUTHORIZED
        assert resp.json()["result"][0]["message"] == AuthenticationError.message
