"""Tests for MFA disable confirmation endpoint (Step 3 of 3-step flow)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.authentication.services.mfa_session import MFASessionService
from apps.shared.test.client import TestClient
from apps.users import UsersCRUD
from apps.users.db.schemas import UserSchema
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
        UserSchema(
            mfa_enabled=True,
            mfa_secret=encrypted,
        ),
    )

    # Refresh and verify
    updated = await crud.get_by_id(user.id)
    assert updated is not None
    assert updated.mfa_secret is not None

    return updated


@pytest.mark.usefixtures("user")
class TestMFADisableConfirm:
    """Test MFA disable confirmation endpoint."""

    disable_initiate_url = "/users/me/mfa/totp/disable/initiate"
    disable_verify_url = "/users/me/mfa/totp/disable/verify"
    disable_confirm_url = "/users/me/mfa/totp/disable/confirm"

    async def test_confirm_with_valid_token_disables_mfa(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Valid confirmation token successfully disables MFA."""
        client.login(user_with_mfa)

        # Step 1: Initiate
        response = await client.post(self.disable_initiate_url)
        assert response.status_code == status.HTTP_200_OK
        mfa_token = response.json()["result"]["mfaToken"]

        # Step 2: Verify code
        assert user_with_mfa.mfa_secret is not None
        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)

        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()["result"]
        assert result["codeValidated"] is True
        confirmation_token = result["confirmationToken"]
        assert confirmation_token != ""

        # Step 3: Confirm disable
        confirm_data = {"confirmationToken": confirmation_token}
        response = await client.post(self.disable_confirm_url, data=confirm_data)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()["result"]
        assert result["mfaDisabled"] is True
        assert "successfully disabled" in result["message"].lower()

        # Verify MFA is disabled in database
        crud = UsersCRUD(session)
        updated_user = await crud.get_by_id(user_with_mfa.id)
        assert updated_user.mfa_enabled is False
        assert updated_user.mfa_secret is None
        assert updated_user.pending_mfa_secret is None
        assert updated_user.mfa_disabled_at is not None

    async def test_confirm_without_token_fails(self, client: TestClient, user_with_mfa: User):
        """Confirmation without confirmationToken returns validation error."""
        client.login(user_with_mfa)

        # Try to confirm without token
        response = await client.post(self.disable_confirm_url, data={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_confirm_with_invalid_token_fails(self, client: TestClient, user_with_mfa: User):
        """Confirmation with invalid token returns error."""
        client.login(user_with_mfa)

        # Try to confirm with fake token (JWT decode fails, returns 401)
        confirm_data = {"confirmationToken": "invalid.jwt.token"}
        response = await client.post(self.disable_confirm_url, data=confirm_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_confirm_with_wrong_purpose_fails(self, client: TestClient, user_with_mfa: User):
        """Confirmation with token from wrong purpose (not disable_confirmed) fails."""
        client.login(user_with_mfa)

        # Get a token with 'disable' purpose (not 'disable_confirmed')
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        # Try to use initiate token in confirm endpoint
        confirm_data = {"confirmationToken": mfa_token}
        response = await client.post(self.disable_confirm_url, data=confirm_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_confirm_clears_mfa_session(self, client: TestClient, user_with_mfa: User):
        """Confirming disable clears the MFA session."""
        client.login(user_with_mfa)

        # Complete verify step to get confirmation token
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        assert user_with_mfa.mfa_secret is not None
        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)

        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data)
        confirmation_token = response.json()["result"]["confirmationToken"]

        # Get session ID
        mfa_service = MFASessionService()
        session_id, _, _ = await mfa_service.validate_and_get_session(confirmation_token)

        # Confirm disable
        confirm_data = {"confirmationToken": confirmation_token}
        response = await client.post(self.disable_confirm_url, data=confirm_data)
        assert response.status_code == status.HTTP_200_OK

        # Verify session is deleted
        session_data = await mfa_service.get_session(session_id)
        assert session_data is None

    async def test_confirm_without_prior_verify_fails(self, client: TestClient, user_with_mfa: User):
        """Cannot confirm without first completing verify step."""
        client.login(user_with_mfa)

        # Try to use initiate token directly in confirm (skipping verify)
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        confirm_data = {"confirmationToken": mfa_token}
        response = await client.post(self.disable_confirm_url, data=confirm_data)

        # Should fail because purpose is 'disable' not 'disable_confirmed'
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_cannot_reuse_confirmation_token(self, client: TestClient, user_with_mfa: User):
        """Confirmation token can only be used once."""
        client.login(user_with_mfa)

        # Complete full flow once
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        assert user_with_mfa.mfa_secret is not None
        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)

        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data)
        confirmation_token = response.json()["result"]["confirmationToken"]

        confirm_data = {"confirmationToken": confirmation_token}
        response = await client.post(self.disable_confirm_url, data=confirm_data)
        assert response.status_code == status.HTTP_200_OK

        # Try to reuse the same confirmation token (session deleted, JWT validation fails with 401)
        response = await client.post(self.disable_confirm_url, data=confirm_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_confirm_invalidates_recovery_codes(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Confirming disable invalidates all recovery codes."""
        from apps.authentication.cruds.recovery_code import RecoveryCodeCRUD
        from apps.authentication.services.recovery_codes import generate_recovery_codes

        client.login(user_with_mfa)

        # Generate recovery codes for the user
        await generate_recovery_codes(session, user_with_mfa.id)

        # Verify codes were created
        recovery_crud = RecoveryCodeCRUD(session)
        existing_codes = await recovery_crud.get_by_user_id(user_with_mfa.id)
        assert len(existing_codes) == 10

        # Complete disable flow
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        assert user_with_mfa.mfa_secret is not None
        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)

        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data)
        confirmation_token = response.json()["result"]["confirmationToken"]

        confirm_data = {"confirmationToken": confirmation_token}
        response = await client.post(self.disable_confirm_url, data=confirm_data)
        assert response.status_code == status.HTTP_200_OK

        # Verify recovery codes are deleted
        remaining_codes = await recovery_crud.get_by_user_id(user_with_mfa.id)
        assert len(remaining_codes) == 0
