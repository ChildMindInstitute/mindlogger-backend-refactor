import http
import uuid
from unittest.mock import ANY, AsyncMock

import pytest

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import RefreshAccessTokenRequest
from apps.authentication.router import router as auth_router
from apps.authentication.services import AuthenticationService
from apps.authentication.tests.factories import UserLogoutRequestFactory
from apps.shared.test import BaseTest
from apps.users import UsersCRUD
from apps.users.domain import UserCreateRequest
from apps.users.router import router as user_router
from infrastructure.http.domain import MindloggerContentSource


@pytest.fixture
def device_id() -> uuid.UUID:
    return uuid.uuid4()


class TestAuthentication(BaseTest):
    user_create_url = user_router.url_path_for("user_create")
    login_url = auth_router.url_path_for("get_token")
    delete_token_url = auth_router.url_path_for("delete_access_token")
    refresh_access_token_url = auth_router.url_path_for("refresh_access_token")

    create_request_user = UserCreateRequest(
        email="tom2@mindlogger.com",
        first_name="Tom",
        last_name="Isaak",
        password="Test1234!",
    )
    create_request_logout_user = UserLogoutRequestFactory.build()

    async def test_get_token(self, session, client):
        # Creating new user
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Authorize user
        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )
        response = await client.post(
            url=self.login_url,
            data=login_request_user.dict(),
        )

        user = await UsersCRUD(session).get_by_email(
            email=self.create_request_user.dict()["email"]
        )

        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]
        assert set(data.keys()) == {"user", "token"}
        assert data["user"]["id"] == str(user.id)

    async def test_delete_access_token(self, client):
        # Creating new user
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Authorize user
        login_request_user = UserLoginRequest(
            **self.create_request_user.dict()
        )
        await client.login(
            url=self.login_url,
            **login_request_user.dict(),
        )

        response = await client.post(
            url=self.delete_token_url,
        )

        assert response.status_code == http.HTTPStatus.OK

    async def test_refresh_access_token(self, client):
        # Creating new user
        internal_response = await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Creating Refresh access token
        refresh_access_token_request = RefreshAccessTokenRequest(
            refresh_token=AuthenticationService.create_refresh_token(
                {
                    "sub": str(internal_response.json()["result"]["id"]),
                    "jti": str(uuid.uuid4()),
                }
            )
        )

        response = await client.post(
            url=self.refresh_access_token_url,
            data=refresh_access_token_request.dict(),
        )

        assert response.status_code == http.HTTPStatus.OK

    async def test_login_and_logout_device(self, client, device_id):
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict(), device_id=str(device_id)
        )
        response = await client.post(
            url=self.login_url,
            data=login_request_user.dict(),
        )
        assert response.status_code == http.HTTPStatus.OK

        await client.login(
            self.login_url,
            self.create_request_user.email,
            self.create_request_user.password,
        )

        response = await client.post(
            url=self.delete_token_url,
            data=dict(device_id=device_id),
        )

        assert response.status_code == http.HTTPStatus.OK

    async def test_login_event_log_is_created_after_login(
        self, mock_activity_log: AsyncMock, client
    ):
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )
        response = await client.post(
            url=self.login_url,
            data=login_request_user.dict(),
        )
        assert response.status_code == http.HTTPStatus.OK
        mock_activity_log.assert_awaited_once()

    @pytest.mark.parametrize(
        "header_value,dest_value",
        (
            (MindloggerContentSource.admin, MindloggerContentSource.admin),
            (MindloggerContentSource.mobile, MindloggerContentSource.mobile),
            (MindloggerContentSource.web, MindloggerContentSource.web),
            (
                MindloggerContentSource.undefined,
                MindloggerContentSource.undefined,
            ),
            ("test", MindloggerContentSource.undefined),
        ),
    )
    async def test_login_if_default_mindollger_content_source_header_is_undefined(  # noqa: E501
        self,
        mock_activity_log: AsyncMock,
        client,
        header_value: str,
        dest_value: str,
    ):
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )
        response = await client.post(
            url=self.login_url,
            data=login_request_user.dict(),
            headers={"Mindlogger-Content-Source": header_value},
        )
        assert response.status_code == http.HTTPStatus.OK
        user_id = uuid.UUID(response.json()["result"]["user"]["id"])
        mock_activity_log.assert_awaited_once_with(
            user_id, None, ANY, ANY, ANY, dest_value
        )
