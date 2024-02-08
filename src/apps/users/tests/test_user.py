import pytest
from pydantic import EmailError
from starlette import status

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.router import router as auth_router
from apps.shared.domain import to_camelcase
from apps.shared.test import BaseTest
from apps.users import UsersCRUD
from apps.users.domain import UserCreateRequest
from apps.users.errors import PasswordHasSpacesError, UserIsDeletedError
from apps.users.router import router as user_router
from apps.users.tests.factories import UserUpdateRequestFactory


class TestUser(BaseTest):
    get_token_url = auth_router.url_path_for("get_token")
    user_create_url = user_router.url_path_for("user_create")
    user_retrieve_url = user_router.url_path_for("user_retrieve")
    user_update_url = user_router.url_path_for("user_update")
    user_delete_url = user_router.url_path_for("user_delete")

    create_request_user = UserCreateRequest(
        email="tom2@mindlogger.com",
        first_name="Tom",
        last_name="Isaak",
        password="Test1234!",
    )
    user_update_request = UserUpdateRequestFactory.build()

    async def test_user_create(self, client):
        # Creating new user
        response = await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()["result"]
        for k, v in self.create_request_user:
            if k != "password":
                assert v == result[to_camelcase(k)]

    async def test_user_create_exist(self, client):
        # Creating new user
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        # Creating a user that already exists
        response = await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_user_retrieve(self, client):
        # Creating new user
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )

        # User get token
        await client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        # User retrieve
        response = await client.get(self.user_retrieve_url)
        assert response.status_code == status.HTTP_200_OK

    async def test_user_update(self, client):
        # Creating new user
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )

        # User get token
        await client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        # User update
        response = await client.put(
            self.user_update_url, data=self.user_update_request.dict()
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_user_delete(self, session, client):
        """UsersCRUD.get_by_email should raise an error
        if user is deleted.
        """
        # Creating new user
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Authorize user
        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )
        await client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        # Delete user
        response = await client.delete(
            self.user_delete_url,
        )

        with pytest.raises(UserIsDeletedError):
            await UsersCRUD(session).get_by_email(login_request_user.email)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_create_user_password_contains_whitespaces(self, client):
        data = self.create_request_user.dict()
        data["password"] = "Test1234 !"
        response = await client.post(self.user_create_url, data=data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == PasswordHasSpacesError.message

    async def test_create_user_not_valid_email(self, client):
        data = self.create_request_user.dict()
        data["email"] = "tom2@mindlogger@com"
        response = await client.post(self.user_create_url, data=data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == EmailError.msg_template
