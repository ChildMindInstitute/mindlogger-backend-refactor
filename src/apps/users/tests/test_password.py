import datetime
import uuid
from unittest.mock import patch

from httpx import Response as HttpResponse
from starlette import status

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.router import router as auth_router
from apps.shared.domain import Response
from apps.shared.test import BaseTest
from apps.users.domain import PasswordRecoveryRequest, PublicUser
from apps.users.router import router as user_router
from apps.users.services import PasswordRecoveryCache
from apps.users.tests.factories import (
    CacheEntryFactory,
    PasswordRecoveryInfoFactory,
    PasswordUpdateRequestFactory,
    UserCreateRequestFactory,
)
from infrastructure.database import transaction


class TestPassword(BaseTest):
    get_token_url = auth_router.url_path_for("get_token")
    user_create_url = user_router.url_path_for("user_create")
    password_update_url = user_router.url_path_for("password_update")
    password_recovery_url = user_router.url_path_for("password_recovery")
    password_recovery_approve_url = user_router.url_path_for(
        "password_recovery_approve"
    )

    create_request_user = UserCreateRequestFactory.build()

    cache_entry = CacheEntryFactory.build(
        instance=PasswordRecoveryInfoFactory.build(
            email=create_request_user.dict()["email"],
        ),
        created_at=datetime.datetime.now(),
    )

    @transaction.rollback
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

    @transaction.rollback
    @patch("apps.users.services.core.MailingService.send")
    @patch("apps.users.services.core.PasswordRecoveryCache.set")
    @patch("apps.users.services.core.PasswordRecoveryCache.delete_all_entries")
    async def test_password_recovery(
        self,
        cache_delete_all_entries_mock,
        cache_set_mock,
        mailing_send_mock,
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

        assert (
            cache_delete_all_entries_mock
            is PasswordRecoveryCache.delete_all_entries
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == internal_response.json()
        assert cache_delete_all_entries_mock.call_count == 1
        assert cache_set_mock.call_count == 1
        assert mailing_send_mock.call_count == 1

    @transaction.rollback
    @patch("apps.users.services.core.PasswordRecoveryCache.delete_all_entries")
    @patch(
        "apps.users.services.core.PasswordRecoveryCache.get",
        return_value=cache_entry,
    )
    async def test_password_recovery_approve(
        self,
        cache_get_mock,
        cache_delete_all_entries_mock,
    ):
        # Creating new user
        internal_response: Response[PublicUser] = await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        expected_result = internal_response.json()

        key = str(
            uuid.uuid3(uuid.uuid4(), self.create_request_user.dict()["email"])
        )

        data = {
            "email": self.create_request_user.dict()["email"],
            "key": key,
            "password": "new_password",
        }

        response = await self.client.post(
            url=self.password_recovery_approve_url,
            data=data,
        )

        assert cache_get_mock is PasswordRecoveryCache.get
        assert (
            cache_delete_all_entries_mock
            is PasswordRecoveryCache.delete_all_entries
        )
        assert cache_get_mock.call_count == 1
        assert cache_delete_all_entries_mock.call_count == 1
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result
