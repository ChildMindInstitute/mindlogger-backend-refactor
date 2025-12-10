"""Tests for concurrent MFA setup race condition prevention."""

import pyotp
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.shared.test.client import TestClient
from apps.users import UsersCRUD
from apps.users.domain import User
from apps.users.services.totp import totp_service


@pytest.fixture
async def user_with_mfa(session: AsyncSession, user: User) -> User:
    """Create user with MFA already enabled."""
    crud = UsersCRUD(session)
    secret = totp_service.generate_secret()
    encrypted_secret = totp_service.encrypt_secret(secret)

    await crud.update_by_id(
        user.id,
        {  # type: ignore[arg-type]
            "mfa_enabled": True,
            "mfa_secret": encrypted_secret,
        },
    )

    updated_user = await crud.get_by_id(user.id)
    assert updated_user is not None
    return updated_user


@pytest.mark.usefixtures("user")
class TestMFAConcurrentSetup:
    """Test MFA concurrent setup prevention."""

    totp_initiate_url = "/users/me/mfa/totp/initiate"
    totp_verify_url = "/users/me/mfa/totp/verify"

    async def test_mfa_totp_initiate_already_enabled_fails(self, client: TestClient, user_with_mfa: User):
        """Test that initiating MFA setup when already enabled returns error."""
        client.login(user_with_mfa)

        response = await client.post(self.totp_initiate_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = response.json()["result"][0]
        assert error["message"] == "Two-factor authentication is already enabled for your account."

    async def test_mfa_totp_verify_concurrent_tabs_only_one_succeeds(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test that only one tab can complete MFA setup in race condition."""
        client.login(user)

        # Tab 1: Initiate
        response1 = await client.post(self.totp_initiate_url)
        assert response1.status_code == status.HTTP_200_OK
        uri1 = response1.json()["result"]["provisioningUri"]
        secret1 = uri1.split("secret=")[1].split("&")[0]

        # Tab 2: Initiate (overwrites pending secret)
        response2 = await client.post(self.totp_initiate_url)
        assert response2.status_code == status.HTTP_200_OK
        uri2 = response2.json()["result"]["provisioningUri"]
        secret2 = uri2.split("secret=")[1].split("&")[0]

        # Secrets should be different
        assert secret1 != secret2

        # Tab 2: Completes first
        code2 = pyotp.TOTP(secret2).now()
        verify2 = await client.post(self.totp_verify_url, data={"code": code2})
        assert verify2.status_code == status.HTTP_200_OK

        # Verify MFA is now enabled in database
        crud = UsersCRUD(session)
        updated_user = await crud.get_by_id(user.id)
        assert updated_user.mfa_enabled is True

        # Tab 1: Tries to complete (should fail - MFA already enabled)
        code1 = pyotp.TOTP(secret1).now()
        verify1 = await client.post(self.totp_verify_url, data={"code": code1})
        assert verify1.status_code == status.HTTP_400_BAD_REQUEST
        error = verify1.json()["result"][0]
        assert error["message"] == "Two-factor authentication is already enabled for your account."

    async def test_mfa_totp_verify_race_condition_both_tabs_different_codes(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test race condition where both tabs have different secrets from different initiate calls."""
        client.login(user)

        # Simulate: Tab 1 initiates, Tab 2 initiates (overwrites), Tab 1 tries old code
        # This is the original bug scenario from the issue

        # Tab 1: Initiate
        response1 = await client.post(self.totp_initiate_url)
        uri1 = response1.json()["result"]["provisioningUri"]
        secret1 = uri1.split("secret=")[1].split("&")[0]

        # Tab 2: Initiate (overwrites pending_mfa_secret)
        response2 = await client.post(self.totp_initiate_url)
        uri2 = response2.json()["result"]["provisioningUri"]
        secret2 = uri2.split("secret=")[1].split("&")[0]

        # Tab 1: Tries to verify with code from old secret (should fail - wrong secret in DB)
        code1 = pyotp.TOTP(secret1).now()
        verify1 = await client.post(self.totp_verify_url, data={"code": code1})
        assert verify1.status_code == status.HTTP_400_BAD_REQUEST
        # Will fail with InvalidTOTPCodeError because secret1 doesn't match pending_mfa_secret (secret2)

        # Tab 2: Successfully verifies with correct secret
        code2 = pyotp.TOTP(secret2).now()
        verify2 = await client.post(self.totp_verify_url, data={"code": code2})
        assert verify2.status_code == status.HTTP_200_OK

        # Verify MFA is enabled
        crud = UsersCRUD(session)
        updated_user = await crud.get_by_id(user.id)
        assert updated_user.mfa_enabled is True

        # Tab 1: Tries again after Tab 2 succeeded (should fail - MFA already enabled)
        code1_new = pyotp.TOTP(secret1).now()
        verify1_retry = await client.post(self.totp_verify_url, data={"code": code1_new})
        assert verify1_retry.status_code == status.HTTP_400_BAD_REQUEST
        error = verify1_retry.json()["result"][0]
        assert error["message"] == "Two-factor authentication is already enabled for your account."

    async def test_mfa_can_be_disabled_and_reenabled(self, client: TestClient, user: User, session: AsyncSession):
        """Test that after disabling MFA, user can set it up again."""
        client.login(user)

        # First setup
        response1 = await client.post(self.totp_initiate_url)
        uri1 = response1.json()["result"]["provisioningUri"]
        secret1 = uri1.split("secret=")[1].split("&")[0]
        code1 = pyotp.TOTP(secret1).now()
        verify1 = await client.post(self.totp_verify_url, data={"code": code1})
        assert verify1.status_code == status.HTTP_200_OK

        # Verify enabled
        crud = UsersCRUD(session)
        user_after_enable = await crud.get_by_id(user.id)
        assert user_after_enable.mfa_enabled is True

        # Disable MFA (directly via CRUD for simplicity in this test)
        from datetime import datetime, timezone

        await crud.disable_mfa(user_id=user.id, disabled_at=datetime.now(timezone.utc).replace(tzinfo=None))

        # Verify disabled
        user_after_disable = await crud.get_by_id(user.id)
        assert user_after_disable.mfa_enabled is False
        assert user_after_disable.mfa_secret is None

        # Re-enable MFA (should succeed since MFA is disabled)
        response2 = await client.post(self.totp_initiate_url)
        assert response2.status_code == status.HTTP_200_OK
        uri2 = response2.json()["result"]["provisioningUri"]
        secret2 = uri2.split("secret=")[1].split("&")[0]
        code2 = pyotp.TOTP(secret2).now()
        verify2 = await client.post(self.totp_verify_url, data={"code": code2})
        assert verify2.status_code == status.HTTP_200_OK

        # Verify re-enabled
        user_after_reenable = await crud.get_by_id(user.id)
        assert user_after_reenable.mfa_enabled is True


@pytest.mark.usefixtures("user_with_mfa")
class TestMFAConcurrentDisable:
    """Test MFA concurrent disable prevention."""

    totp_disable_initiate_url = "/users/me/mfa/totp/disable/initiate"
    totp_disable_verify_url = "/users/me/mfa/totp/disable/verify"

    async def test_mfa_totp_disable_initiate_already_disabled_fails(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test that initiating MFA disable when already disabled returns error."""
        # Ensure MFA is disabled
        crud = UsersCRUD(session)
        from datetime import datetime, timezone

        await crud.disable_mfa(user_id=user.id, disabled_at=datetime.now(timezone.utc).replace(tzinfo=None))

        # Verify disabled
        updated_user = await crud.get_by_id(user.id)
        assert updated_user.mfa_enabled is False

        client.login(updated_user)

        # Try to initiate disable
        response = await client.post(self.totp_disable_initiate_url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        error = response.json()["result"][0]
        assert error["message"] == "MFA is not enabled for this account."

    async def test_mfa_totp_disable_concurrent_tabs_only_one_succeeds(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test that only one tab can complete MFA disable in race condition."""
        client.login(user_with_mfa)

        # Get the current MFA secret for TOTP codes
        crud = UsersCRUD(session)
        current_user = await crud.get_by_id(user_with_mfa.id)
        decrypted_secret = totp_service.decrypt_secret(current_user.mfa_secret)

        # Tab 1: Initiate disable
        response1 = await client.post(self.totp_disable_initiate_url)
        assert response1.status_code == status.HTTP_200_OK
        mfa_token1 = response1.json()["result"]["mfaToken"]

        # Tab 2: Initiate disable
        response2 = await client.post(self.totp_disable_initiate_url)
        assert response2.status_code == status.HTTP_200_OK
        mfa_token2 = response2.json()["result"]["mfaToken"]

        # Tokens should be different
        assert mfa_token1 != mfa_token2

        # Tab 1: Completes first with valid TOTP
        code1 = pyotp.TOTP(decrypted_secret).now()
        verify1 = await client.post(self.totp_disable_verify_url, data={"code": code1, "mfaToken": mfa_token1})
        assert verify1.status_code == status.HTTP_200_OK

        # Verify MFA is now disabled in database
        updated_user = await crud.get_by_id(user_with_mfa.id)
        assert updated_user.mfa_enabled is False
        assert updated_user.mfa_secret is None

        # Tab 2: Tries to complete (should fail - MFA already disabled)
        code2 = pyotp.TOTP(decrypted_secret).now()
        verify2 = await client.post(self.totp_disable_verify_url, data={"code": code2, "mfaToken": mfa_token2})
        assert verify2.status_code == status.HTTP_403_FORBIDDEN
        error = verify2.json()["result"][0]
        assert error["message"] == "MFA is not enabled for this account."

    async def test_mfa_totp_disable_race_condition_with_expired_session(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test race condition where Tab 1 completes disable while Tab 2 has expired session."""
        client.login(user_with_mfa)

        # Get the current MFA secret
        crud = UsersCRUD(session)
        current_user = await crud.get_by_id(user_with_mfa.id)
        decrypted_secret = totp_service.decrypt_secret(current_user.mfa_secret)

        # Tab 1: Initiate disable
        response1 = await client.post(self.totp_disable_initiate_url)
        mfa_token1 = response1.json()["result"]["mfaToken"]

        # Tab 2: Initiate disable
        response2 = await client.post(self.totp_disable_initiate_url)
        mfa_token2 = response2.json()["result"]["mfaToken"]

        # Tab 1: Successfully disables MFA
        code1 = pyotp.TOTP(decrypted_secret).now()
        verify1 = await client.post(self.totp_disable_verify_url, data={"code": code1, "mfaToken": mfa_token1})
        assert verify1.status_code == status.HTTP_200_OK

        # Verify MFA disabled
        updated_user = await crud.get_by_id(user_with_mfa.id)
        assert updated_user.mfa_enabled is False

        # Tab 2: Tries with its token (should fail - MFA already disabled)
        # Note: Even if token is still valid, the mfa_enabled check will catch this
        code2 = pyotp.TOTP(decrypted_secret).now()
        verify2 = await client.post(self.totp_disable_verify_url, data={"code": code2, "mfaToken": mfa_token2})
        assert verify2.status_code == status.HTTP_403_FORBIDDEN
        error = verify2.json()["result"][0]
        assert error["message"] == "MFA is not enabled for this account."
