import uuid

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import RefreshAccessTokenRequest
from apps.authentication.router import router as auth_router
from apps.authentication.services import AuthenticationService
from apps.authentication.tests.factories import UserLogoutRequestFactory
from apps.shared.test import BaseTest
from apps.users import UsersCRUD
from apps.users.domain import UserCreateRequest
from apps.users.router import router as user_router


class TestAuthentication(BaseTest):
    user_create_url = user_router.url_path_for("user_create")
    get_token_url = auth_router.url_path_for("get_token")
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
        await client.post(self.user_create_url, data=self.create_request_user.dict())

        # Authorize user
        login_request_user: UserLoginRequest = UserLoginRequest(**self.create_request_user.dict())
        response = await client.post(
            url=self.get_token_url,
            data=login_request_user.dict(),
        )

        user = await UsersCRUD(session).get_by_email(email=self.create_request_user.dict()["email"])

        assert response.status_code == 200
        data = response.json()["result"]
        assert set(data.keys()) == {"user", "token"}
        assert data["user"]["id"] == str(user.id)

    async def test_delete_access_token(self, client):
        # Creating new user
        await client.post(self.user_create_url, data=self.create_request_user.dict())

        # Authorize user
        login_request_user = UserLoginRequest(**self.create_request_user.dict())
        await client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        response = await client.post(
            url=self.delete_token_url,
        )

        assert response.status_code == 200

    async def test_refresh_access_token(self, client):
        # Creating new user
        internal_response = await client.post(self.user_create_url, data=self.create_request_user.dict())

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

        assert response.status_code == 200

    async def test_login_and_logout_device(self, client):
        await client.post(self.user_create_url, data=self.create_request_user.dict())
        device_id = str(uuid.uuid4())

        login_request_user: UserLoginRequest = UserLoginRequest(**self.create_request_user.dict(), device_id=device_id)
        response = await client.post(
            url=self.get_token_url,
            data=login_request_user.dict(),
        )
        assert response.status_code == 200

        await client.login(
            self.get_token_url,
            self.create_request_user.email,
            self.create_request_user.password,
        )

        response = await client.post(
            url=self.delete_token_url,
            data=dict(device_id=device_id),
        )

        assert response.status_code == 200
