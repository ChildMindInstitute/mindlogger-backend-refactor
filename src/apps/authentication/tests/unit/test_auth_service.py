import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pytest import FixtureRequest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.crud import TokenBlacklistCRUD
from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import InternalToken
from apps.authentication.domain.token.internal import TokenPayload, TokenPurpose
from apps.authentication.errors import BadCredentials, InvalidCredentials
from apps.authentication.services import AuthenticationService
from apps.authentication.services.core import TokensService
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User
from apps.users.errors import UserIsDeletedError, UserNotFound
from config import settings
from infrastructure.http.domain import MindloggerContentSource

TEST_PASSWORD = "Test12345!"
RJTI = str(uuid.uuid4())


class TestAuthService:
    def test_verify_password__raise_exception(self, auth_service: AuthenticationService):
        password = "password"
        hashed_password = auth_service.get_password_hash(password)
        with pytest.raises(BadCredentials):
            auth_service.verify_password("broken_pass", hashed_password)

    def test_verify_password__mute_error(self, auth_service: AuthenticationService):
        password = "password"
        hashed_password = auth_service.get_password_hash(password)
        valid = auth_service.verify_password("broken_pass", hashed_password, raise_exception=False)
        assert not valid

    def test_verify_password(self, auth_service: AuthenticationService):
        password = "password"
        hashed_password = auth_service.get_password_hash(password)
        valid = auth_service.verify_password(password, hashed_password)
        assert valid

    def test_verify_password__normalized_hash(self, auth_service: AuthenticationService):
        """n + combining ~ (decomposed) and ñ (composed) should NFKC normalize and verify against each other."""
        decomposed = "grancaban\u0303a"  # grancabaña with n + combining ~ (decomposed)
        composed = "grancaba\u00f1a"  # grancabaña with ñ (composed)
        decomposed_hash = auth_service.get_password_hash(decomposed)
        composed_hash = auth_service.get_password_hash(composed)
        assert auth_service.verify_password(composed, decomposed_hash)
        assert auth_service.verify_password(decomposed, decomposed_hash)
        assert auth_service.verify_password(composed, composed_hash)
        assert auth_service.verify_password(decomposed, composed_hash)

    def test_verify_password__unnormalized_hash(self, auth_service: AuthenticationService):
        """Old hashes from unnormalized input should still verify via fallback."""
        from apps.shared.bcrypt import get_password_hash as raw_get_password_hash

        decomposed = "grancaban\u0303a"  # grancabaña with n + combining ~ (decomposed)
        unnormalized_hash = raw_get_password_hash(decomposed)  # old hash without NFKC normalization
        assert auth_service.verify_password(decomposed, unnormalized_hash)

    async def test_authenticate_user__creds_are_not_valid(self, auth_service: AuthenticationService, user: User):
        login_schema = UserLoginRequest(email=user.email_encrypted, password="notvalidpassword")
        with pytest.raises(InvalidCredentials):
            await auth_service.authenticate_user(login_schema)

    async def test_authenticate_user__user_not_found(self, auth_service: AuthenticationService):
        login_schema = UserLoginRequest(email="notexisting@example.com", password=TEST_PASSWORD)
        with pytest.raises(UserNotFound):
            await auth_service.authenticate_user(login_schema)

    async def test_authenticate_user__is_deleted(
        self, auth_service: AuthenticationService, user: User, session: AsyncSession
    ):
        user_crud = UsersCRUD(session)
        deleted = await user_crud.delete(user.id)
        assert deleted.is_deleted
        login_schema = UserLoginRequest(email=user.email_encrypted, password=TEST_PASSWORD)
        with pytest.raises(UserIsDeletedError):
            await auth_service.authenticate_user(login_schema)

    async def test_authenticate_user(self, auth_service: AuthenticationService, user: User):
        login_schema = UserLoginRequest(email=user.email_encrypted, password=TEST_PASSWORD)
        act = await auth_service.authenticate_user(login_schema)
        assert act.id == user.id

    async def test_revoke_access_token__there_is_no_rjti(
        self,
        auth_service: AuthenticationService,
        access_token_internal: InternalToken,
        mocker: MockerFixture,
    ):
        mock = mocker.patch("apps.authentication.services.core.TokensService.revoke")
        access_token_internal.payload.rjti = None
        await auth_service.revoke_token(access_token_internal, TokenPurpose.ACCESS)
        mock.assert_awaited_once_with(access_token_internal, TokenPurpose.ACCESS)

    async def test_revoke_access_token(
        self,
        auth_service: AuthenticationService,
        access_token_internal: InternalToken,
        mocker: MockerFixture,
    ):
        mock = mocker.patch("apps.authentication.services.core.TokensService.revoke")
        await auth_service.revoke_token(access_token_internal, TokenPurpose.ACCESS)
        mock.assert_any_await(access_token_internal, TokenPurpose.ACCESS)
        refresh_token = auth_service._get_refresh_token_by_access(access_token_internal)
        mock.assert_any_await(refresh_token, TokenPurpose.REFRESH)

    async def test_revoke_refresh_token(
        self,
        auth_service: AuthenticationService,
        refresh_token_internal: InternalToken,
        mocker: MockerFixture,
    ):
        mock = mocker.patch("apps.authentication.services.core.TokensService.revoke")
        await auth_service.revoke_token(refresh_token_internal, TokenPurpose.REFRESH)
        mock.assert_awaited_once_with(refresh_token_internal, TokenPurpose.REFRESH)


class TestTokenService:
    async def test_token_is_revoked(self, token_blacklist_service: TokensService, access_token_internal: InternalToken):
        is_revoked = await token_blacklist_service.is_revoked(access_token_internal)
        assert not is_revoked

    @pytest.mark.parametrize(
        "token_fixture,purpose",
        (("access_token_internal", TokenPurpose.ACCESS), ("refresh_token_internal", TokenPurpose.REFRESH)),
    )
    async def test_token_revoke(
        self,
        token_blacklist_service: TokensService,
        token_fixture: str,
        purpose: TokenPurpose,
        request: FixtureRequest,
    ):
        token = request.getfixturevalue(token_fixture)
        await token_blacklist_service.revoke(token, purpose)
        is_revoked = await token_blacklist_service.is_revoked(token)
        assert is_revoked

    async def test_token_revoke__token_already_revoked(
        self, token_blacklist_service: TokensService, access_token_internal: InternalToken, mocker: MockerFixture
    ):
        await token_blacklist_service.revoke(access_token_internal, TokenPurpose.ACCESS)
        is_revoked = await token_blacklist_service.is_revoked(access_token_internal)
        assert is_revoked
        mock = mocker.patch("apps.authentication.crud.TokenBlacklistCRUD.create")
        await token_blacklist_service.revoke(access_token_internal, TokenPurpose.ACCESS)
        mock.assert_not_awaited()

    async def test_token_revoke__concurrent_revocations_of_same_token(
        self, session: AsyncSession, access_token_internal: InternalToken
    ):
        """Two requests revoking the same token both pass the is_revoked check before either
        inserts, so the second insert must not violate the unique constraint on jti."""
        crud = TokenBlacklistCRUD(session)
        await crud.create(access_token_internal, TokenPurpose.ACCESS)
        await crud.create(access_token_internal, TokenPurpose.ACCESS)
        assert await crud.exists(access_token_internal)

    async def test_token_revoke__ttl_less_than_one(
        self, token_blacklist_service: TokensService, access_token_internal: InternalToken, mocker: MockerFixture
    ):
        access_token_internal.payload.exp = 0
        await token_blacklist_service.revoke(access_token_internal, TokenPurpose.ACCESS)
        is_revoked = await token_blacklist_service.is_revoked(access_token_internal)
        assert not is_revoked


class TestRefreshTokenExpDerivation:
    """`_get_refresh_token_by_access` must derive the paired refresh exp using the
    same per-client lifetimes the tokens were minted with (keyed on the `client` claim)."""

    @staticmethod
    def _access_token(access_exp: datetime, client: MindloggerContentSource | None) -> InternalToken:
        return InternalToken(
            payload=TokenPayload(
                sub=uuid.uuid4(),
                exp=int(access_exp.timestamp()),
                jti=str(uuid.uuid4()),
                rjti=RJTI,
                client=client,
            )
        )

    def test_web_admin_uses_short_deltas(self, auth_service: AuthenticationService, mocker: MockerFixture):
        mocker.patch.object(settings.authentication.access_token, "web_admin_expiration", 15)
        mocker.patch.object(settings.authentication.refresh_token, "web_admin_expiration", 120)
        access_exp = datetime.now(timezone.utc) + timedelta(minutes=15)
        derived = auth_service._get_refresh_token_by_access(
            self._access_token(access_exp, MindloggerContentSource.admin)
        )
        assert derived is not None
        expected = int((access_exp - timedelta(minutes=15) + timedelta(minutes=120)).timestamp())
        assert derived.payload.exp == expected
        assert derived.payload.jti == RJTI

    def test_legacy_client_none_uses_defaults(self, auth_service: AuthenticationService, mocker: MockerFixture):
        mocker.patch.object(settings.authentication.access_token, "web_admin_expiration", 15)
        mocker.patch.object(settings.authentication.refresh_token, "web_admin_expiration", 120)
        access_exp = datetime.now(timezone.utc) + timedelta(minutes=settings.authentication.access_token.expiration)
        derived = auth_service._get_refresh_token_by_access(self._access_token(access_exp, None))
        assert derived is not None
        expected = int(
            (
                access_exp
                - timedelta(minutes=settings.authentication.access_token.expiration)
                + timedelta(minutes=settings.authentication.refresh_token.expiration)
            ).timestamp()
        )
        assert derived.payload.exp == expected
