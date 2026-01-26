"""Tests for TOTP code verification during MFA disable."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

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
class TestMFADisableVerify:
    """Test TOTP code verification during MFA disable."""

    disable_initiate_url = "/users/me/mfa/totp/disable/initiate"
    disable_verify_url = "/users/me/mfa/totp/disable/verify"

    async def test_disable_verify_with_valid_totp_returns_confirmation_token(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Valid TOTP code returns confirmation token but does NOT disable MFA yet."""
        client.login(user_with_mfa)

        # Initiate disable flow
        response = await client.post(self.disable_initiate_url)
        assert response.status_code == status.HTTP_200_OK
        mfa_token = response.json()["result"]["mfaToken"]

        # Decrypt the secret to generate valid TOTP
        assert user_with_mfa.mfa_secret is not None
        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)

        # Verify with valid TOTP
        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["result"]
        assert result["codeValidated"] is True
        assert "confirmationToken" in result
        assert result["confirmationToken"] != ""
        assert "confirm" in result["message"].lower()

        # Verify MFA is STILL ENABLED in database (not disabled yet)
        crud = UsersCRUD(session)
        updated_user = await crud.get_by_id(user_with_mfa.id)
        assert updated_user.mfa_enabled is True  # Still enabled!
        assert updated_user.mfa_secret is not None  # Secret still exists!

    async def test_disable_verify_with_invalid_totp_returns_error(self, client: TestClient, user_with_mfa: User):
        """Invalid TOTP code returns error."""
        client.login(user_with_mfa)

        # Initiate disable flow
        response = await client.post(self.disable_initiate_url)
        assert response.status_code == status.HTTP_200_OK
        mfa_token = response.json()["result"]["mfaToken"]

        # Use invalid TOTP
        verify_data = {"mfaToken": mfa_token, "code": "000000"}
        response = await client.post(self.disable_verify_url, data=verify_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = response.json()["result"][0]
        assert "invalid" in error["message"].lower() or "incorrect" in error["message"].lower()

    async def test_disable_verify_without_mfa_token_fails(self, client: TestClient, user_with_mfa: User):
        """Verification without mfaToken returns error."""
        client.login(user_with_mfa)

        # Try to verify without initiating
        verify_data = {"code": "123456"}
        response = await client.post(self.disable_verify_url, data=verify_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
