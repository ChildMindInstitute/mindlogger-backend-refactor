import pytest
from starlette import status

from apps.authentication.router import router as auth_router
from apps.shared.domain import Response
from apps.shared.test import BaseTest
from apps.users import UsersCRUD
from apps.users.domain import PublicUser, User, UserLoginRequest
from apps.users.errors import UserIsDeletedError
from apps.users.router import router as user_router
from apps.users.tests.factories import (
    UserCreateRequestFactory,
    UserUpdateRequestFactory,
)
from infrastructure.database import transaction


class TestUser(BaseTest):

    get_token_url = auth_router.url_path_for("get_token")
    user_create_url = user_router.url_path_for("user_create")
    user_retrieve_url = user_router.url_path_for("user_retrieve")
    user_update_url = user_router.url_path_for("user_update")
    user_delete_url = user_router.url_path_for("user_delete")

    create_request_user = UserCreateRequestFactory.build()
    user_update_request = UserUpdateRequestFactory.build()

    @transaction.rollback
    async def test_user_create(self):
        # Creating new user
        response = await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        # Get  created user by email
        created_user: User = await UsersCRUD().get_by_email(
            self.create_request_user.email
        )

        public_user = PublicUser(**created_user.dict())

        expected_result: Response[PublicUser] = Response(result=public_user)

        count = await UsersCRUD().count()

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == expected_result.dict(by_alias=True)
        assert count == expected_result.result.id

    @transaction.rollback
    async def test_user_create_exist(self):
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        # Creating a user that already exists
        response = await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @transaction.rollback
    async def test_user_retrieve(self):
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )

        # User get token
        await self.client.get_token(
            url=self.get_token_url,
            user_login_request=login_request_user,
        )

        # User retrieve
        response = await self.client.get(self.user_retrieve_url)

        logged_in_user: User = await UsersCRUD().get_by_email(
            self.create_request_user.email
        )

        public_user = PublicUser(**logged_in_user.dict())

        expected_result: Response[PublicUser] = Response(result=public_user)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result.dict(by_alias=True)
        assert response.json()["Result"]["Id"] == expected_result.result.id

    @transaction.rollback
    async def test_user_update(self):
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )

        # User get token
        await self.client.get_token(
            url=self.get_token_url,
            user_login_request=login_request_user,
        )

        # User update
        response = await self.client.put(
            self.user_update_url, data=self.user_update_request.dict()
        )

        updated_user: User = await UsersCRUD().get_by_email(
            self.create_request_user.email
        )

        public_user = PublicUser(**updated_user.dict())

        expected_result: Response[PublicUser] = Response(result=public_user)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result.dict(by_alias=True)
        assert response.json()["Result"]["Id"] == expected_result.result.id

    @transaction.rollback
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
        await self.client.get_token(
            url=self.get_token_url,
            user_login_request=login_request_user,
        )

        # Delete user
        response = await self.client.delete(
            self.user_delete_url,
        )

        with pytest.raises(UserIsDeletedError):
            await UsersCRUD().get_by_email(login_request_user.email)

        assert response.status_code == status.HTTP_204_NO_CONTENT
