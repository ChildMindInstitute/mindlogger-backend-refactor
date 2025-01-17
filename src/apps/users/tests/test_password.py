import asyncio
import datetime
import uuid
from unittest.mock import ANY, AsyncMock

import pytest
from httpx import Response as HttpResponse
from pytest_mock import MockFixture
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.router import router as auth_router
from apps.mailing.services import TestMail
from apps.shared.test.client import TestClient
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import PasswordRecoveryRequest, User, UserCreate
from apps.users.errors import PasswordHasSpacesError, ReencryptionInProgressError
from apps.users.router import router as user_router
from apps.users.tests.factories import CacheEntryFactory, PasswordRecoveryInfoFactory, PasswordUpdateRequestFactory
from config import settings
from infrastructure.cache import PasswordRecoveryHealthCheckNotValid
from infrastructure.utility import RedisCache


@pytest.fixture(scope="class")
def cache_entry(user: UserCreate):
    return CacheEntryFactory.build(
        instance=PasswordRecoveryInfoFactory.build(
            email=user.email,
        ),
        created_at=datetime.datetime.now(datetime.UTC),
    )


@pytest.mark.usefixtures("mock_reencrypt_kiq", "cache_entry")
class TestPassword:
    get_token_url = auth_router.url_path_for("get_token")
    user_create_url = user_router.url_path_for("user_create")
    password_update_url = user_router.url_path_for("password_update")
    password_recovery_url = user_router.url_path_for("password_recovery")
    password_recovery_approve_url = user_router.url_path_for("password_recovery_approve")
    password_recovery_healthcheck_url = user_router.url_path_for("password_recovery_healthcheck")

    async def test_password_update(
        self, mock_reencrypt_kiq: AsyncMock, client: TestClient, user: User, user_create: UserCreate
    ):
        # User get token
        client.login(user)

        # Password update
        password_update_request = PasswordUpdateRequestFactory.build(prev_password=user_create.password)
        response: HttpResponse = await client.put(self.password_update_url, data=password_update_request.dict())
        assert response.status_code == status.HTTP_200_OK

        # User get token with new password
        login_request_user = UserLoginRequest(
            email=user_create.email,
            password=password_update_request.dict()["password"],
        )

        internal_response: HttpResponse = await client.post(
            url=self.get_token_url,
            data=login_request_user.dict(),
        )

        assert internal_response.status_code == status.HTTP_200_OK
        mock_reencrypt_kiq.assert_awaited_once()

    async def test_password_recovery(self, client: TestClient, user_create: UserCreate, mailbox: TestMail):
        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = PasswordRecoveryRequest(email=user_create.dict()["email"])

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        cache = RedisCache()

        assert response.status_code == status.HTTP_201_CREATED
        keys = await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*")
        assert len(keys) == 1
        assert password_recovery_request.email in keys[0]
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].recipients[0] == password_recovery_request.email
        assert mailbox.mails[0].subject == "Password reset"

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED

        new_keys = await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*")
        assert len(keys) == 1
        assert keys[0] != new_keys[0]
        assert len(mailbox.mails) == 2
        assert mailbox.mails[0].recipients[0] == password_recovery_request.email

    async def test_password_recovery_admin(self, client: TestClient, user_create: UserCreate, mailbox: TestMail):
        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = PasswordRecoveryRequest(email=user_create.dict()["email"])

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
            headers={"MindLogger-Content-Source": "admin"},
        )

        cache = RedisCache()

        assert response.status_code == status.HTTP_201_CREATED
        keys = await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*")
        assert len(keys) == 1
        assert password_recovery_request.email in keys[0]
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].recipients[0] == password_recovery_request.email
        assert mailbox.mails[0].subject == "Password reset"

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED

        new_keys = await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*")
        assert len(keys) == 1
        assert keys[0] != new_keys[0]
        assert len(mailbox.mails) == 2
        assert mailbox.mails[0].recipients[0] == password_recovery_request.email

    async def test_password_recovery_mobile(self, client: TestClient, user_create: UserCreate, mailbox: TestMail):
        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = PasswordRecoveryRequest(email=user_create.dict()["email"])

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
            headers={"MindLogger-Content-Source": "mobile"},
        )

        cache = RedisCache()

        assert response.status_code == status.HTTP_201_CREATED
        keys = await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*")
        assert len(keys) == 1
        assert password_recovery_request.email in keys[0]
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].recipients[0] == password_recovery_request.email
        assert mailbox.mails[0].subject == "Password reset"

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED

        new_keys = await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*")
        assert len(keys) == 1
        assert keys[0] != new_keys[0]
        assert len(mailbox.mails) == 2
        assert mailbox.mails[0].recipients[0] == password_recovery_request.email

    async def test_password_recovery_invalid(self, client: TestClient, user_create: UserCreate, mailbox: TestMail):
        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = PasswordRecoveryRequest(email=user_create.dict()["email"])

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
            headers={"MindLogger-Content-Source": "invalid-content-source"},
        )

        cache = RedisCache()

        assert response.status_code == status.HTTP_201_CREATED
        keys = await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*")
        assert len(keys) == 1
        assert password_recovery_request.email in keys[0]
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].recipients[0] == password_recovery_request.email
        assert mailbox.mails[0].subject == "Password reset"

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED

        new_keys = await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*")
        assert len(keys) == 1
        assert keys[0] != new_keys[0]
        assert len(mailbox.mails) == 2
        assert mailbox.mails[0].recipients[0] == password_recovery_request.email

    async def test_password_recovery_approve(self, client: TestClient, user_create: UserCreate):
        cache = RedisCache()

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = PasswordRecoveryRequest(email=user_create.dict()["email"])

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED
        key = (await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*"))[0].split(":")[-1]

        data = {
            "email": user_create.dict()["email"],
            "key": key,
            "password": "new_password",
        }

        response = await client.post(
            url=self.password_recovery_approve_url,
            data=data,
        )
        assert response.status_code == status.HTTP_200_OK
        keys = await cache.keys(key="PasswordRecoveryCache:{user_create.email}*")
        assert len(keys) == 0

    async def test_password_recovery_approve_expired(self, client: TestClient, user_create: UserCreate):
        cache = RedisCache()
        settings.authentication.password_recover.expiration = 1

        # Password recovery
        password_recovery_request: PasswordRecoveryRequest = PasswordRecoveryRequest(email=user_create.dict()["email"])

        response = await client.post(
            url=self.password_recovery_url,
            data=password_recovery_request.dict(),
        )

        assert response.status_code == status.HTTP_201_CREATED
        key = (await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*"))[0].split(":")[-1]
        await asyncio.sleep(2)

        data = {
            "email": user_create.dict()["email"],
            "key": key,
            "password": "new_password",
        }

        response = await client.post(
            url=self.password_recovery_approve_url,
            data=data,
        )

        keys = await cache.keys(key=f"PasswordRecoveryCache:{user_create.email}*")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert len(keys) == 0

    async def test_update_password__password_contains_whitespaces(
        self, client: TestClient, user_create: UserCreate, user: User
    ):
        client.login(user)

        data = {
            "password": user_create.password + " ",
            "prev_password": user_create.password,
        }
        resp = await client.put(self.password_update_url, data=data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == PasswordHasSpacesError.message

    async def test_update_password__reencryption_already_in_progress(
        self, client: TestClient, user_create: UserCreate, mocker: MockFixture, user: User
    ):
        client.login(user)

        data = {
            "password": user_create.password,
            "prev_password": user_create.password,
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

    async def test_password_recovery__update_user_email_encrypted_if_no_email_encrypted(
        self, client: TestClient, user_create: UserCreate, user: User, mocker: MockFixture, session: AsyncSession
    ):
        client.login(user)
        updated = await UsersCRUD(session).update_encrypted_email(user, "")
        assert not updated.email_encrypted
        spy = mocker.spy(UsersCRUD, "update_encrypted_email")
        response = await client.post(url=self.password_recovery_url, data={"email": user_create.email})
        assert response.status_code == status.HTTP_201_CREATED
        spy.assert_awaited_once_with(ANY, ANY, user_create.email)
