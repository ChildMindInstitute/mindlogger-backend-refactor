import pytest
from starlette import status

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.router import router as auth_router
from apps.shared.test import BaseTest
from apps.users import UsersCRUD
from apps.users.errors import UserIsDeletedError
from apps.users.router import router as user_router
from apps.users.tests.factories import (
    UserCreateRequestFactory,
    UserUpdateRequestFactory,
)
from infrastructure.database import rollback


class TestUser(BaseTest):
    get_token_url = auth_router.url_path_for("get_token")
    user_create_url = user_router.url_path_for("user_create")
    user_retrieve_url = user_router.url_path_for("user_retrieve")
    user_update_url = user_router.url_path_for("user_update")
    user_delete_url = user_router.url_path_for("user_delete")

    create_request_user = UserCreateRequestFactory.build()
    user_update_request = UserUpdateRequestFactory.build()

    @rollback
    async def test_user_create(self):
        # Creating new user
        response = await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        assert response.status_code == status.HTTP_201_CREATED, response.json()

    @rollback
    async def test_user_create_exist(self):
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        # Creating a user that already exists
        response = await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    @rollback
    async def test_user_retrieve(self):
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )

        # User get token
        await self.client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        # User retrieve
        response = await self.client.get(self.user_retrieve_url)
        assert response.status_code == status.HTTP_200_OK

    @rollback
    async def test_user_update(self):
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )

        # User get token
        await self.client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        # User update
        response = await self.client.put(
            self.user_update_url, data=self.user_update_request.dict()
        )

        assert response.status_code == status.HTTP_200_OK

    @rollback
    async def test_user_delete(self):
        """UsersCRUD.get_by_email should raise an error
        if user is deleted.
        """
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Authorize user
        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )
        await self.client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        # Delete user
        response = await self.client.delete(
            self.user_delete_url,
        )

        with pytest.raises(UserIsDeletedError):
            await UsersCRUD().get_by_email(login_request_user.email)

        assert response.status_code == status.HTTP_204_NO_CONTENT
