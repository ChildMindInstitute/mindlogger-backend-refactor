from unittest.mock import patch

from starlette import status

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import RefreshAccessTokenRequest
from apps.authentication.router import router as auth_router
from apps.authentication.services import AuthenticationService
from apps.authentication.tests.factories import UserLogoutRequestFactory
from apps.shared.test import BaseTest
from apps.users import UsersCRUD
from apps.users.router import router as user_router
from apps.users.tests import UserCreateRequestFactory
from infrastructure.database import transaction


class TestAuthentication(BaseTest):
    user_create_url = user_router.url_path_for("user_create")
    get_token_url = auth_router.url_path_for("get_token")
    delete_token_url = auth_router.url_path_for("delete_access_token")
    refresh_access_token_url = auth_router.url_path_for("refresh_access_token")

    create_request_user = UserCreateRequestFactory.build()
    create_request_logout_user = UserLogoutRequestFactory.build()

    @transaction.rollback
    async def test_get_token(self):
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Authorize user
        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )
        response = await self.client.post(
            url=self.get_token_url,
            data=login_request_user.dict(),
        )

        user = await UsersCRUD().get_by_email(
            email=self.create_request_user.dict()["email"]
        )

        access_token = AuthenticationService.create_access_token(
            {"sub": str(user.id)}
        )

        refresh_token = AuthenticationService.create_refresh_token(
            {"sub": str(user.id)}
        )

        assert response.status_code == status.HTTP_200_OK
        assert (
            response.json()["result"]["token"]["accessToken"] == access_token
        )
        assert (
            response.json()["result"]["token"]["refreshToken"] == refresh_token
        )
        assert response.json()["result"]["user"]["id"] == str(user.id)

    @transaction.rollback
    @patch("apps.authentication.services.core.TokensBlacklistCache.set")
    async def test_delete_access_token(
        self,
        cache_set_mock,
    ):
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Authorize user
        login_request_user = UserLoginRequest(
            **self.create_request_user.dict()
        )
        await self.client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        response = await self.client.post(
            url=self.delete_token_url,
            data=self.create_request_logout_user.dict(),
        )

        assert cache_set_mock.call_count == 1
        assert response.status_code == status.HTTP_200_OK

    @transaction.rollback
    async def test_refresh_access_token(self):
        # Creating new user
        internal_response = await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Creating Refresh access token
        refresh_access_token_request = RefreshAccessTokenRequest(
            refresh_token=AuthenticationService.create_refresh_token(
                {"sub": str(internal_response.json()["result"]["id"])}
            )
        )

        response = await self.client.post(
            url=self.refresh_access_token_url,
            data=refresh_access_token_request.dict(),
        )

        assert response.status_code == status.HTTP_200_OK
