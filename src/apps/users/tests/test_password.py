from starlette import status

from apps.authentication.router import router as auth_router
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
from apps.users.tests.factories import (
    PasswordUpdateRequestFactory,
    UserCreateRequestFactory,
)
from infrastructure.database import transaction


class TestPassword(BaseTest):
    # fixtures = ["users/fixtures/users.json"]

    get_token_url = auth_router.url_path_for("get_token")
    user_create_url = user_router.url_path_for("user_create")
    password_update_url = user_router.url_path_for("password_update")
    password_recovery_url = user_router.url_path_for("password_recovery")
    password_recovery_approve_url = user_router.url_path_for(
        "password_recovery_approve"
    )

    create_request_user = UserCreateRequestFactory.build()
    password_update_request = PasswordUpdateRequestFactory.build()

    password_recovery_request: PasswordRecoveryRequest = (
        PasswordRecoveryRequest(email="tom@mindlogger.com")
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

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_result.dict(by_alias=True)

        # User get token with new password
        login_request_user: UserLoginRequest = UserLoginRequest(
            email=self.create_request_user.dict()["email"],
            password=self.password_update_request.dict()["password"],
        )

        response = await self.client.get_token(
            url=self.get_token_url,
            user_login_request=login_request_user,
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_password_recovery(self, mocker):
        # Creating new user
        await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )

        login_request_user: UserLoginRequest = UserLoginRequest(
            **self.create_request_user.dict()
        )
        await self.client.get_token(
            url=self.get_token_url,
            user_login_request=login_request_user,
        )
        cache_delete_all_entries = mocker.patch(
            "apps.users.services.core.PasswordRecoveryService._cache.delete_all_entries"
        )
        cache_set = mocker.patch(
            "apps.users.services.core.PasswordRecoveryService._cache.set"
        )
        mail_send = mocker.patch(
            "apps.users.services.core.MailingService.send"
        )

        response = await self.client.put(
            self.password_recovery_url,
            data=self.password_recovery_request.dict(),
        )

        internal_response: Response[PublicUser] = Response[PublicUser](
            **response.json()
        )
        
        # TODO: Add user here
        # expected_result = Response[PublicUser]()

        assert cache_delete_all_entries.call_count == 1
        assert cache_set.call_count == 1
        assert mail_send.call_count == 1
        # assert internal_response.result == expected_result

    async def test_password_recovery_approve(self):
        pass
