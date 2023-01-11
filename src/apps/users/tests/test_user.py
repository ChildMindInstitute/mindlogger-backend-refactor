from starlette import status

from apps.shared.domain import Response
from apps.shared.test import BaseTest
from apps.users import UserSchema, UsersCRUD
from apps.users.domain import (
    PublicUser,
    User,
    UserCreateRequest,
    UserLoginRequest,
    UserUpdateRequest,
)
from infrastructure.database import transaction


class TestUser(BaseTest):
    fixtures = ["users/fixtures/users.json"]

    login_url = "/auth/token"
    user_create_url = "/users"
    user_retrieve_url = "/users/me"
    user_update_url = "/users/me"
    user_delete_url = "/users/me"
    password_update_url = "/users/me/password"
    password_recovery_url = "/users/me/password/recover"
    password_recovery_approve_url = "/users/me/password/recover/approve"

    create_request_user_new: UserCreateRequest = UserCreateRequest(
        email="tom_new@mindlogger.com",
        full_name="Tom Isaak",
        password="Test1234!",
    )

    create_request_user_exist: UserCreateRequest = UserCreateRequest(
        email="tom@mindlogger.com",
        full_name="Tom Isaak",
        password="Test1234!",
    )

    login_request_user: UserLoginRequest = UserLoginRequest(
        email="tom@mindlogger.com",
        password="Test1234!",
    )

    user_update_request: UserUpdateRequest = UserUpdateRequest(
        full_name="Isaak Tom"
    )

    @transaction.rollback
    async def test_creating_user(self):
        # Creating new user
        response = await self.client.post(
            self.user_create_url, data=self.create_request_user_new.dict()
        )
        created_user: User = await UsersCRUD().get_by_email(
            self.create_request_user_new.email
        )

        public_user = PublicUser(**created_user.dict())

        expected_result: Response[PublicUser] = Response(result=public_user)

        count = await UsersCRUD().count()

        assert response.status_code == status.HTTP_201_CREATED, expected_result
        assert count == expected_result.result.id

    @transaction.rollback
    async def test_creating_user_exist(self):
        # Creating a user that already exists
        response = await self.client.post(
            self.user_create_url, data=self.create_request_user_exist.dict()
        )

        expected_result = {"messages": ["User already exists"]}

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == expected_result

    @transaction.rollback
    async def test_retrieving_user(self):
        await self.client.login(
            self.login_url,
            self.login_request_user.email,
            self.login_request_user.password,
        )

        response = await self.client.get(self.user_retrieve_url)

        logged_in_user: User = await UsersCRUD().get_by_email(
            self.login_request_user.email
        )

        public_user = PublicUser(**logged_in_user.dict())

        expected_result: Response[PublicUser] = Response(result=public_user)

        assert response.status_code == status.HTTP_200_OK, expected_result
        assert response.json()["Result"]["Id"] == expected_result.result.id

    @transaction.rollback
    async def test_updating_user(self):
        await self.client.login(
            self.login_url,
            self.login_request_user.email,
            self.login_request_user.password,
        )

        response = await self.client.put(
            self.user_update_url, data=self.user_update_request.dict()
        )

        updated_user: User = await UsersCRUD().get_by_email(
            self.login_request_user.email
        )

        public_user = PublicUser(**updated_user.dict())

        expected_result: Response[PublicUser] = Response(result=public_user)

        assert response.status_code == status.HTTP_200_OK, expected_result
        assert response.json()["Result"]["Id"] == expected_result.result.id

    @transaction.rollback
    async def test_deleting_user(self):
        await self.client.login(
            self.login_url,
            self.login_request_user.email,
            self.login_request_user.password,
        )

        response = await self.client.delete(
            self.user_delete_url,
        )

        instance: UserSchema = await UsersCRUD()._get(
            key="email", value=self.login_request_user.email
        )

        assert instance.is_deleted is True
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""
