"""Tests for end-to-end MFA disable flow integration."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.authentication.services.mfa_session import MFASessionService
from apps.shared.test.client import TestClient
from apps.users import UsersCRUD
from apps.users.domain import User
from apps.users.services.totp import totp_service


@pytest.fixture
async def user_with_mfa(session: AsyncSession, user: User) -> User:
    """Create user with MFA already enabled."""
    # Generate and encrypt TOTP secret
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)

    # Enable MFA
    crud = UsersCRUD(session)
    await crud.update_by_id(
        user.id,
        {  # type: ignore[arg-type]
            "mfa_enabled": True,
            "mfa_secret": encrypted,
        },
    )

    # Refresh and verify
    updated = await crud.get_by_id(user.id)
    assert updated is not None
    assert updated.mfa_secret is not None

    return updated


@pytest.mark.usefixtures("user")
class TestMFADisableIntegration:
    """Test end-to-end MFA disable flow integration."""

    disable_initiate_url = "/users/me/mfa/totp/disable/initiate"
    disable_verify_url = "/users/me/mfa/totp/disable/verify"

    async def test_complete_mfa_disable_flow_end_to_end(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Complete flow from initiation to successful disable works end-to-end."""
        client.login(user_with_mfa)

        # Step 1: Initiate disable
        initiate_response = await client.post(self.disable_initiate_url)
        assert initiate_response.status_code == status.HTTP_200_OK

        initiate_result = initiate_response.json()["result"]
        assert initiate_result["mfaRequired"] is True
        mfa_token = initiate_result["mfaToken"]
        assert mfa_token != ""

        # Step 2: Generate valid TOTP
        assert user_with_mfa.mfa_secret is not None

        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)

        # Step 3: Verify and complete disable
        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        verify_response = await client.post(self.disable_verify_url, data=verify_data)
        assert verify_response.status_code == status.HTTP_200_OK

        verify_result = verify_response.json()["result"]
        assert verify_result["mfaDisabled"] is True

        # Step 4: Verify all MFA data cleared in database
        crud = UsersCRUD(session)
        final_user = await crud.get_by_id(user_with_mfa.id)
        assert final_user.mfa_enabled is False
        assert final_user.mfa_secret is None
        assert final_user.pending_mfa_secret is None
        assert final_user.pending_mfa_created_at is None
        assert final_user.last_totp_time_step is None
        assert final_user.mfa_disabled_at is not None

    async def test_mfa_disable_clears_all_sessions(self, client: TestClient, user_with_mfa: User):
        """Disabling MFA clears the MFA session after completion."""
        client.login(user_with_mfa)

        # Initiate disable
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        # Get session ID before disable
        mfa_service = MFASessionService()
        session_id, _, _ = await mfa_service.validate_and_get_session(mfa_token)

        # Verify session exists
        session_data = await mfa_service.get_session(session_id)
        assert session_data is not None

        # Complete disable flow
        assert user_with_mfa.mfa_secret is not None

        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)
        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        await client.post(self.disable_verify_url, data=verify_data)

        # Verify session was deleted
        session_data_after = await mfa_service.get_session(session_id)
        assert session_data_after is None

    async def test_cannot_reuse_mfa_token_after_successful_disable(self, client: TestClient, user_with_mfa: User):
        """MFA token cannot be reused after successful disable."""
        client.login(user_with_mfa)

        # Complete disable flow
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        assert user_with_mfa.mfa_secret is not None

        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)
        verify_data = {"mfaToken": mfa_token, "code": valid_totp}

        # First verification succeeds
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_200_OK

        # Try to reuse the same token
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_cannot_initiate_disable_after_already_disabled(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Cannot initiate disable flow if MFA is already disabled."""
        client.login(user_with_mfa)

        # Complete disable flow
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        assert user_with_mfa.mfa_secret is not None

        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)
        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        await client.post(self.disable_verify_url, data=verify_data)

        # Refresh user to get updated state
        crud = UsersCRUD(session)
        disabled_user = await crud.get_by_id(user_with_mfa.id)
        client.login(disabled_user)

        # Try to initiate disable again
        response = await client.post(self.disable_initiate_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_concurrent_disable_attempts_only_one_succeeds(self, client: TestClient, user_with_mfa: User):
        """Only one concurrent disable attempt can succeed."""
        client.login(user_with_mfa)

        # Initiate two disable flows
        response1 = await client.post(self.disable_initiate_url)
        mfa_token1 = response1.json()["result"]["mfaToken"]

        response2 = await client.post(self.disable_initiate_url)
        mfa_token2 = response2.json()["result"]["mfaToken"]

        # Both tokens should be different (different sessions)
        assert mfa_token1 != mfa_token2

        # Complete first disable
        assert user_with_mfa.mfa_secret is not None

        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)
        verify_data1 = {"mfaToken": mfa_token1, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data1)
        assert response.status_code == status.HTTP_200_OK

        # Second disable attempt should fail (MFA already disabled)
        verify_data2 = {"mfaToken": mfa_token2, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data2)
        # Should fail because MFA is already disabled
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        )

    async def test_failed_verification_does_not_disable_mfa(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Failed TOTP verification does not disable MFA."""
        client.login(user_with_mfa)

        # Initiate disable
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        # Try with invalid TOTP
        verify_data = {"mfaToken": mfa_token, "code": "000000"}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify MFA still enabled
        crud = UsersCRUD(session)
        user = await crud.get_by_id(user_with_mfa.id)
        assert user.mfa_enabled is True
        assert user.mfa_secret is not None
