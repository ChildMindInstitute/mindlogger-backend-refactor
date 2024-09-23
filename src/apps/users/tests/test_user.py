from typing import cast

import pytest
from pydantic import EmailError, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.authentication.router import router as auth_router
from apps.shared.domain import to_camelcase
from apps.shared.test.client import TestClient
from apps.users import UsersCRUD
from apps.users.domain import AppInfoOS, User, UserCreate, UserCreateRequest, UserDeviceCreate
from apps.users.errors import PasswordHasSpacesError, UserIsDeletedError
from apps.users.router import router as user_router
from apps.users.tests.factories import UserUpdateRequestFactory


@pytest.fixture
def request_data() -> UserCreateRequest:
    return UserCreateRequest(
        email=EmailStr("tom2@mindlogger.com"),
        first_name="Tom",
        last_name="Isaak",
        password="Test1234!",
    )


@pytest.fixture
def device_create_data() -> UserDeviceCreate:
    return UserDeviceCreate(os=AppInfoOS(name="os1", version="1.0.0"), app_version="1.1.1", device_id="device#id")


@pytest.mark.usefixtures("user")
class TestUser:
    get_token_url = auth_router.url_path_for("get_token")
    user_create_url = user_router.url_path_for("user_create")
    user_retrieve_url = user_router.url_path_for("user_retrieve")
    user_update_url = user_router.url_path_for("user_update")
    user_delete_url = user_router.url_path_for("user_delete")
    user_devices_url = user_router.url_path_for("user_save_device")

    user_update_request = UserUpdateRequestFactory.build()

    async def test_user_create(self, client: TestClient, request_data: UserCreateRequest):
        response = await client.post(self.user_create_url, data=request_data.dict())
        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()["result"]
        for k, v in request_data:
            if k != "password":
                assert v == result[to_camelcase(k)]

    async def test_user_create_exist(
        self, client: TestClient, request_data: UserCreateRequest, user_create: UserCreate
    ):
        request_data.email = user_create.email
        response = await client.post(self.user_create_url, data=request_data.dict())
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_user_retrieve(self, client: TestClient, user: User):
        client.login(user)
        response = await client.get(self.user_retrieve_url)
        assert response.status_code == status.HTTP_200_OK

    async def test_user_update(self, client: TestClient, user: User):
        client.login(user)
        response = await client.put(self.user_update_url, data=self.user_update_request.dict())
        assert response.status_code == status.HTTP_200_OK

    async def test_user_delete(self, session: AsyncSession, client: TestClient, user: User):
        client.login(user)
        response = await client.delete(
            self.user_delete_url,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        with pytest.raises(UserIsDeletedError):
            user.email_encrypted = cast(str, user.email_encrypted)
            await UsersCRUD(session).get_by_email(user.email_encrypted)

    async def test_create_user_password_contains_whitespaces(self, client: TestClient, request_data: UserCreateRequest):
        data = request_data.dict()
        data["password"] = "Test1234 !"
        response = await client.post(self.user_create_url, data=data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == PasswordHasSpacesError.message

    async def test_create_user_not_valid_email(self, client: TestClient, request_data: UserCreateRequest):
        data = request_data.dict()
        data["email"] = "tom2@mindlogger@com"
        response = await client.post(self.user_create_url, data=data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == EmailError.msg_template

    async def test_user_create_device(self, client: TestClient, device_create_data: UserDeviceCreate, user: User):
        client.login(user)
        payload = device_create_data.copy(deep=True)

        response = await client.post(self.user_devices_url, data=payload.dict(include={"device_id"}))
        assert response.status_code == status.HTTP_200_OK

        result = response.json()["result"]
        assert set(result.keys()) == {"appVersion", "createdAt", "deviceId", "id", "os", "updatedAt", "userId"}
        assert result["userId"] == str(user.id)
        assert result["os"] is None

        # full data
        response = await client.post(self.user_devices_url, data=payload)
        assert response.status_code == status.HTTP_200_OK
        result_same_device = response.json()["result"]
        assert result_same_device["id"] == result["id"]
        assert result_same_device["createdAt"] == result["createdAt"]
        assert result_same_device["createdAt"] != result_same_device["updatedAt"]

        for k, v in payload.dict(by_alias=True).items():
            assert result_same_device[k] == v

        # empty data don't clear stored one
        response = await client.post(self.user_devices_url, data=payload.dict(include={"device_id"}))
        assert response.status_code == status.HTTP_200_OK

        result = response.json()["result"]
        for k, v in payload.dict(by_alias=True).items():
            assert result[k] == v
