import datetime
import uuid
from unittest.mock import patch

from starlette import status

from apps.authentication.router import router as auth_router
from apps.mailing.services import MailingService
from apps.shared.domain import Response
from apps.shared.test import BaseTest
from apps.users import UsersCRUD
from apps.users.domain import (
    PasswordRecoveryRequest,
    PublicUser,
    User,
    UserLoginRequest,
)
from apps.users.router import router as user_router
from apps.users.services import PasswordRecoveryCache
from apps.users.tests.factories import (
    PasswordUpdateRequestFactory,
    UserCreateRequestFactory,
    CacheEntryFactory,
    PasswordRecoveryInfoFactory,
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
    password_update_request = PasswordUpdateRequestFactory.build()

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
        await self.client.get_token(
            url=self.get_token_url,
            user_login_request=login_request_user,
        )

        # Password update
        response = await self.client.put(
            self.password_update_url, data=self.password_update_request.dict()
        )

        updated_user: User = await UsersCRUD().get_by_email(
            login_request_user.email
        )

        public_user = PublicUser(**updated_user.dict())

        expected_result: Response[PublicUser] = Response(result=public_user)

        # User get token with new password
        login_request_user: UserLoginRequest = UserLoginRequest(
            email=self.create_request_user.dict()["email"],
            password=self.password_update_request.dict()["password"],
        )

        internal_response = await self.client.get_token(
            url=self.get_token_url,
            user_login_request=login_request_user,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result.dict(by_alias=True)
        assert response.status_code == status.HTTP_200_OK
        assert internal_response.status_code == status.HTTP_200_OK

    @transaction.rollback
    @patch("apps.users.services.core.MailingService.send")
    @patch("apps.users.services.core.PasswordRecoveryCache.set")
    @patch("apps.users.services.core.PasswordRecoveryCache.delete_all_entries")
    async def test_password_recovery(
        self,
        mock_object_delete_all_entries,
        mock_object_set,
        mock_object_send,
    ):
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

        assert (
            mock_object_delete_all_entries
            is PasswordRecoveryCache.delete_all_entries
        )
        assert mock_object_set is PasswordRecoveryCache.set
        assert mock_object_send is MailingService.send
        assert mock_object_delete_all_entries.call_count == 1
        assert mock_object_set.call_count == 1
        assert mock_object_send.call_count == 1
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result

    @transaction.rollback
    @patch("apps.users.services.core.PasswordRecoveryCache.delete_all_entries")
    @patch(
        "apps.users.services.core.PasswordRecoveryCache.get",
        return_value=cache_entry,
    )
    async def test_password_recovery_approve(
        self,
        mock_object_get,
        mock_object_delete_all_entries,
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

        assert mock_object_get is PasswordRecoveryCache.get
        assert (
            mock_object_delete_all_entries
            is PasswordRecoveryCache.delete_all_entries
        )
        assert mock_object_get.call_count == 1
        assert mock_object_delete_all_entries.call_count == 1
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result
