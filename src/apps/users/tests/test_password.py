import asyncio
import datetime

import pytest
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
from infrastructure.database import rollback
from infrastructure.utility import RedisCache


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
        created_at=datetime.datetime.now(),
    )

    @rollback
    async def test_password_update(self):
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

        # Password update
        password_update_request = PasswordUpdateRequestFactory.build(
            prev_password=self.create_request_user.password
        )
        response: HttpResponse = await self.client.put(
            self.password_update_url, data=password_update_request.dict()
        )

        # User get token with new password
        login_request_user: UserLoginRequest = UserLoginRequest(
            email=self.create_request_user.dict()["email"],
            password=password_update_request.dict()["password"],
        )

        internal_response: HttpResponse = await self.client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.status_code == status.HTTP_200_OK
        assert internal_response.status_code == status.HTTP_200_OK

    @pytest.mark.skip
    @rollback
    async def test_password_recovery(
        self,
    ):
        # Creating new user
        internal_response: HttpResponse = await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = (
            PasswordRecoveryRequest(
                email=self.create_request_user.dict()["email"]
            )
        )

        response = await self.client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        cache = RedisCache()

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == internal_response.json()
        keys = await cache.keys()
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

        response = await self.client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == internal_response.json()

        new_keys = await cache.keys()
        assert len(keys) == 1
        assert keys[0] != new_keys[0]
        assert len(TestMail.mails) == 2
        assert (
            TestMail.mails[0].recipients[0] == password_recovery_request.email
        )

    @pytest.mark.skip
    @rollback
    async def test_password_recovery_approve(
        self,
    ):
        cache = RedisCache()

        # Creating new user
        internal_response: Response[PublicUser] = await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        expected_result = internal_response.json()

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = (
            PasswordRecoveryRequest(
                email=self.create_request_user.dict()["email"]
            )
        )

        response = await self.client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_200_OK
        key = (await cache.keys())[0].split(":")[-1]

        data = {
            "email": self.create_request_user.dict()["email"],
            "key": key,
            "password": "new_password",
        }

        response = await self.client.post(
            url=self.password_recovery_approve_url,
            data=data,
        )

        keys = await cache.keys()

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result
        assert len(keys) == 0
        assert len(keys) == 0

    @pytest.mark.skip
    @rollback
    async def test_password_recovery_approve_expired(
        self,
    ):
        cache = RedisCache()
        settings.authentication.password_recover.expiration = 1

        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = (
            PasswordRecoveryRequest(
                email=self.create_request_user.dict()["email"]
            )
        )

        response = await self.client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_200_OK
        key = (await cache.keys())[0].split(":")[-1]
        await asyncio.sleep(2)

        data = {
            "email": self.create_request_user.dict()["email"],
            "key": key,
            "password": "new_password",
        }

        response = await self.client.post(
            url=self.password_recovery_approve_url,
            data=data,
        )

        keys = await cache.keys()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert len(keys) == 0
