import asyncio
import datetime
import uuid
from unittest.mock import AsyncMock

from httpx import Response as HttpResponse
from pytest_mock import MockFixture
from starlette import status

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.router import router as auth_router
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.db.schemas import UserSchema
from apps.users.domain import PasswordRecoveryRequest, UserCreateRequest
from apps.users.errors import PasswordHasSpacesError, ReencryptionInProgressError
from apps.users.router import router as user_router
from apps.users.tests.factories import CacheEntryFactory, PasswordRecoveryInfoFactory, PasswordUpdateRequestFactory
from config import settings
from infrastructure.cache import PasswordRecoveryHealthCheckNotValid
from infrastructure.utility import RedisCache


class TestPassword(BaseTest):
    get_token_url = auth_router.url_path_for("get_token")
    user_create_url = user_router.url_path_for("user_create")
    password_update_url = user_router.url_path_for("password_update")
    password_recovery_url = user_router.url_path_for("password_recovery")
    password_recovery_approve_url = user_router.url_path_for("password_recovery_approve")
    password_recovery_healthcheck_url = user_router.url_path_for("password_recovery_healthcheck")

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

    async def test_password_update(self, mock_reencrypt_kiq, client):
        # Creating new user
        await client.post(self.user_create_url, data=self.create_request_user.dict())

        login_request_user: UserLoginRequest = UserLoginRequest(**self.create_request_user.dict())

        # User get token
        await client.login(
            url=self.get_token_url,
            **login_request_user.dict(),
        )

        # Password update
        password_update_request = PasswordUpdateRequestFactory.build(prev_password=self.create_request_user.password)
        response: HttpResponse = await client.put(self.password_update_url, data=password_update_request.dict())

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
        mock_reencrypt_kiq.assert_awaited_once()

    async def test_password_recovery(
        self,
        mock_reencrypt_kiq: AsyncMock,
        client: TestClient,
    ):
        # Creating new user
        await client.post(self.user_create_url, data=self.create_request_user.dict())

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = PasswordRecoveryRequest(
            email=self.create_request_user.dict()["email"]
        )

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        cache = RedisCache()

        assert response.status_code == status.HTTP_201_CREATED
        keys = await cache.keys(key="PasswordRecoveryCache:tom2@mindlogger.com*")
        assert len(keys) == 1
        assert password_recovery_request.email in keys[0]
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients[0] == password_recovery_request.email
        assert TestMail.mails[0].subject == "Girder for MindLogger (development instance): Temporary access"

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED

        new_keys = await cache.keys(key="PasswordRecoveryCache:tom2@mindlogger.com*")
        assert len(keys) == 1
        assert keys[0] != new_keys[0]
        assert len(TestMail.mails) == 2
        assert TestMail.mails[0].recipients[0] == password_recovery_request.email

    async def test_password_recovery_approve(
        self,
        mock_reencrypt_kiq: AsyncMock,
        client: TestClient,
    ):
        cache = RedisCache()

        # Creating new user
        internal_response = await client.post(self.user_create_url, data=self.create_request_user.dict())

        expected_result = internal_response.json()

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = PasswordRecoveryRequest(
            email=self.create_request_user.dict()["email"]
        )

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED
        key = (await cache.keys(key="PasswordRecoveryCache:tom2@mindlogger.com*"))[0].split(":")[-1]

        data = {
            "email": self.create_request_user.dict()["email"],
            "key": key,
            "password": "new_password",
        }

        response = await client.post(
            url=self.password_recovery_approve_url,
            data=data,
        )

        keys = await cache.keys(key="PasswordRecoveryCache:tom2@mindlogger.com*")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result
        assert len(keys) == 0
        assert len(keys) == 0

    async def test_password_recovery_approve_expired(
        self,
        mock_reencrypt_kiq: AsyncMock,
        client: TestClient,
    ):
        cache = RedisCache()
        settings.authentication.password_recover.expiration = 1

        # Creating new user
        await client.post(self.user_create_url, data=self.create_request_user.dict())

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = PasswordRecoveryRequest(
            email=self.create_request_user.dict()["email"]
        )

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED
        key = (await cache.keys(key="PasswordRecoveryCache:tom2@mindlogger.com*"))[0].split(":")[-1]
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

        keys = await cache.keys(key="PasswordRecoveryCache:tom2@mindlogger.com*")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert len(keys) == 0

    async def test_update_password__password_contains_whitespaces(
        self,
        client: TestClient,
        user_tom_create: UserCreateRequest,
        user_tom: UserSchema,
    ):
        await client.login(
            self.get_token_url,
            user_tom_create.email,
            user_tom_create.password,
        )

        data = {
            "password": user_tom_create.password + " ",
            "prev_password": user_tom_create.password,
        }
        resp = await client.put(self.password_update_url, data=data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == PasswordHasSpacesError.message

    async def test_update_password__reencryption_already_in_progress(
        self,
        client: TestClient,
        user_tom_create: UserCreateRequest,
        user_tom: UserSchema,
        mocker: MockFixture,
    ):
        await client.login(
            self.get_token_url,
            user_tom_create.email,
            user_tom_create.password,
        )

        data = {
            "password": user_tom_create.password,
            "prev_password": user_tom_create.password,
        }
        mock = mocker.patch("apps.job.service.JobService.is_job_in_progress")
        mock.__aenter__.return_value = True
        resp = await client.put(self.password_update_url, data=data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == ReencryptionInProgressError.message

    async def test_password_recovery__user_does_not_exists_error_is_muted(self, client: TestClient):
        resp = await client.post(
            self.password_recovery_url,
            data={"email": "userdoesnotexist@example.com"},
        )
        assert resp.status_code == status.HTTP_201_CREATED

    async def test_password_recovery_heathcheck_link_does_not_exists(self, client: TestClient, uuid_zero: uuid.UUID):
        data = {"email": "email@example.com", "key": str(uuid_zero)}
        resp = await client.get(self.password_recovery_healthcheck_url, query=data)
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == PasswordRecoveryHealthCheckNotValid.message

    async def test_password_recovery_heathcheck_with_result(
        self, client: TestClient, uuid_zero: uuid.UUID, mocker: MockFixture
    ):
        data = {"email": "email@example.com", "key": str(uuid_zero)}
        mocker.patch("apps.users.services.PasswordRecoveryCache.get")
        resp = await client.get(self.password_recovery_healthcheck_url, query=data)
        assert resp.status_code == status.HTTP_200_OK
