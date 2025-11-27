"""Tests for MFA disable initiation endpoint."""

import pytest
from starlette import status

from apps.authentication.services.mfa_session import MFASessionService
from apps.shared.test.client import TestClient
from apps.users import UsersCRUD
from apps.users.domain import User
from apps.users.services.totp import totp_service
from sqlalchemy.ext.asyncio import AsyncSession


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
        {
            "mfa_enabled": True,
            "mfa_secret": encrypted,
        },
    )

    # Refresh and verify
    updated = await crud.get_by_id(user.id)
    assert updated is not None
    assert updated.mfa_secret is not None

    return updated


@pytest.fixture
async def user_no_mfa(session: AsyncSession, user: User) -> User:
    """Ensure user has MFA disabled."""
    crud = UsersCRUD(session)
    await crud.update_by_id(
        user.id,
        {
            "mfa_enabled": False,
            "mfa_secret": None,
        },
    )

    # Refresh and verify
    updated = await crud.get_by_id(user.id)
    assert updated is not None
    assert updated.mfa_secret is None

    return updated


@pytest.mark.usefixtures("user")
class TestMFADisableInitiate:
    """Test MFA disable initiation endpoint."""

    disable_initiate_url = "/users/me/mfa/totp/disable/initiate"

    async def test_disable_requires_mfa_enabled(self, client: TestClient, user_no_mfa: User):
        """User without MFA enabled cannot initiate disable."""
        client.login(user_no_mfa)

        response = await client.post(self.disable_initiate_url)

        # Should return 403 Access Denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Verify error message
        error = response.json()
        assert "MFA is not enabled" in error["result"][0]["message"]

    async def test_disable_with_mfa_enabled_success(self, client: TestClient, user_with_mfa: User):
        """User with MFA enabled can initiate disable."""
        client.login(user_with_mfa)

        response = await client.post(self.disable_initiate_url)

        # Should succeed
        assert response.status_code == status.HTTP_200_OK

        result = response.json()["result"]

        # Verify response structure
        assert result["mfaRequired"] is True
        assert "mfaToken" in result
        assert result["mfaToken"] != ""
        assert "message" in result
        assert "verify your identity" in result["message"].lower()

    async def test_disable_creates_session_with_correct_purpose(
        self, client: TestClient, user_with_mfa: User
    ):
        """Verify session is created with purpose='disable'."""
        client.login(user_with_mfa)

        response = await client.post(self.disable_initiate_url)
        assert response.status_code == status.HTTP_200_OK

        result = response.json()["result"]
        mfa_token = result["mfaToken"]

        # Decode token to get session_id
        mfa_service = MFASessionService()
        session_id, user_id, purpose = await mfa_service.validate_and_get_session(mfa_token)

        # Verify session details
        assert user_id == user_with_mfa.id
        assert purpose == "disable"
        assert session_id is not None

        # Verify session data in Redis
        session_data = await mfa_service.get_session(session_id)
        assert session_data is not None
        assert session_data.user_id == user_with_mfa.id
        assert session_data.purpose == "disable"
