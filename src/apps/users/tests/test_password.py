import asyncio
import datetime
from unittest.mock import patch

from asynctest import CoroutineMock
from httpx import Response as HttpResponse
from starlette import status

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.router import router as auth_router
from apps.mailing.services import TestMail
from apps.shared.domain import Response
from apps.shared.test import BaseTest
from apps.users.domain import (
    PasswordRecoveryRequest,
    PublicUser,
    UserCreateRequest,
)
from apps.users.router import router as user_router
from apps.users.tests.factories import (
    CacheEntryFactory,
    PasswordRecoveryInfoFactory,
    PasswordUpdateRequestFactory,
)
from config import settings
from infrastructure.utility import RedisCache


@patch("apps.users.api.password.reencrypt_answers.kiq")
class TestPassword(BaseTest):
    get_token_url = auth_router.url_path_for("get_token")
    user_create_url = user_router.url_path_for("user_create")
    password_update_url = user_router.url_path_for("password_update")
    password_recovery_url = user_router.url_path_for("password_recovery")
    password_recovery_approve_url = user_router.url_path_for(
        "password_recovery_approve"
    )

    create_request_user = UserCreateRequest(
        email="tom2@mindlogger.com",
        first_name="Tom",
        last_name="Isaak",
        password="Test1234!",
    )

    cache_entry = CacheEntryFactory.build(
        instance=PasswordRecoveryInfoFactory.build(
            email=create_request_user.dict()["email"],
        ),
        created_at=datetime.datetime.utcnow(),
    )

    async def test_password_update(self, task_mock: CoroutineMock, client):
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

        # Password update
        password_update_request = PasswordUpdateRequestFactory.build(
            prev_password=self.create_request_user.password
        )
        response: HttpResponse = await client.put(
            self.password_update_url, data=password_update_request.dict()
        )

        # User get token with new password
        login_request_user = UserLoginRequest(
            email=self.create_request_user.dict()["email"],
            password=password_update_request.dict()["password"],
        )

        internal_response: HttpResponse = await client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.status_code == status.HTTP_200_OK
        assert internal_response.status_code == status.HTTP_200_OK
        task_mock.assert_awaited_once()

    async def test_password_recovery(
        self,
        task_mock: CoroutineMock,
        client,
    ):
        # Creating new user
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = (
            PasswordRecoveryRequest(
                email=self.create_request_user.dict()["email"]
            )
        )

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        cache = RedisCache()

        assert response.status_code == status.HTTP_201_CREATED
        keys = await cache.keys(
            key="PasswordRecoveryCache:tom2@mindlogger.com*"
        )
        assert len(keys) == 1
        assert password_recovery_request.email in keys[0]
        assert len(TestMail.mails) == 1
        assert (
            TestMail.mails[0].recipients[0] == password_recovery_request.email
        )
        assert (
            TestMail.mails[0].subject
            == "Girder for MindLogger (development instance): Temporary access"
        )

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED

        new_keys = await cache.keys(
            key="PasswordRecoveryCache:tom2@mindlogger.com*"
        )
        assert len(keys) == 1
        assert keys[0] != new_keys[0]
        assert len(TestMail.mails) == 2
        assert (
            TestMail.mails[0].recipients[0] == password_recovery_request.email
        )

    async def test_password_recovery_approve(
        self,
        task_mock: CoroutineMock,
        client,
    ):
        cache = RedisCache()

        # Creating new user
        internal_response: Response[PublicUser] = await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        expected_result = internal_response.json()

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = (
            PasswordRecoveryRequest(
                email=self.create_request_user.dict()["email"]
            )
        )

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED
        key = (
            await cache.keys(key="PasswordRecoveryCache:tom2@mindlogger.com*")
        )[0].split(":")[-1]

        data = {
            "email": self.create_request_user.dict()["email"],
            "key": key,
            "password": "new_password",
        }

        response = await client.post(
            url=self.password_recovery_approve_url,
            data=data,
        )

        keys = await cache.keys(
            key="PasswordRecoveryCache:tom2@mindlogger.com*"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result
        assert len(keys) == 0
        assert len(keys) == 0

    async def test_password_recovery_approve_expired(
        self,
        task_mock: CoroutineMock,
        client,
    ):
        cache = RedisCache()
        settings.authentication.password_recover.expiration = 1

        # Creating new user
        await client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = (
            PasswordRecoveryRequest(
                email=self.create_request_user.dict()["email"]
            )
        )

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED
        key = (
            await cache.keys(key="PasswordRecoveryCache:tom2@mindlogger.com*")
        )[0].split(":")[-1]
        await asyncio.sleep(2)

        data = {
            "email": self.create_request_user.dict()["email"],
            "key": key,
            "password": "new_password",
        }

        response = await client.post(
            url=self.password_recovery_approve_url,
            data=data,
        )

        keys = await cache.keys(
            key="PasswordRecoveryCache:tom2@mindlogger.com*"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert len(keys) == 0
