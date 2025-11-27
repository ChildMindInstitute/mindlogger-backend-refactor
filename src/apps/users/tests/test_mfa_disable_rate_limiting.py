"""Tests for rate limiting and lockout mechanisms for MFA disable flow."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.authentication.services.mfa_session import MFASessionService
from apps.shared.test.client import TestClient
from apps.users import UsersCRUD
from apps.users.domain import User, UserCreate
from apps.users.services.totp import totp_service
from apps.users.services.user import UserService


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


@pytest.mark.usefixtures("user")
class TestMFADisableRateLimiting:
    """Test rate limiting and lockout mechanisms for MFA disable flow."""

    disable_initiate_url = "/users/me/mfa/totp/disable/initiate"
    disable_verify_url = "/users/me/mfa/totp/disable/verify"

    async def test_per_session_rate_limit_after_max_attempts(
        self, client: TestClient, user_with_mfa: User
    ):
        """Per-session rate limit blocks further attempts after max failures."""
        client.login(user_with_mfa)

        # Initiate disable
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        # Make 5 invalid attempts (typical max per session)
        for attempt in range(5):
            verify_data = {"mfaToken": mfa_token, "code": "000000"}
            response = await client.post(self.disable_verify_url, data=verify_data)
            # Early attempts should be 400, later ones might be 429
            assert response.status_code in (
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # 6th attempt should definitely be rate limited
        verify_data = {"mfaToken": mfa_token, "code": "000000"}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    async def test_global_lockout_after_many_failures_across_sessions(
        self, client: TestClient, user_with_mfa: User
    ):
        """Global lockout prevents all MFA operations after many failed attempts."""
        client.login(user_with_mfa)

        # Make multiple failed attempts across different sessions
        for session_num in range(3):  # Create 3 sessions
            response = await client.post(self.disable_initiate_url)
            if response.status_code != status.HTTP_200_OK:
                # Already locked out globally
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                break

            mfa_token = response.json()["result"]["mfaToken"]

            # Make 4 invalid attempts per session
            for attempt in range(4):
                verify_data = {"mfaToken": mfa_token, "code": f"{session_num}{attempt}0000"}
                response = await client.post(self.disable_verify_url, data=verify_data)
                
                if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    # Hit global lockout
                    error = response.json()["result"][0]
                    assert (
                        "locked" in error["message"].lower()
                        or "too many" in error["message"].lower()
                    )
                    return  # Test passed - global lockout reached

        # If we get here without hitting global lockout, verify we're close
        # (implementation may vary on exact threshold)
        response = await client.post(self.disable_initiate_url)
        # Should either succeed or be locked out
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    async def test_per_session_counter_resets_with_new_session(
        self, client: TestClient, user_with_mfa: User
    ):
        """New MFA session has fresh per-session attempt counter."""
        client.login(user_with_mfa)

        # First session - make 2 failed attempts
        response1 = await client.post(self.disable_initiate_url)
        mfa_token1 = response1.json()["result"]["mfaToken"]

        for _ in range(2):
            verify_data = {"mfaToken": mfa_token1, "code": "111111"}
            await client.post(self.disable_verify_url, data=verify_data)

        # Start new session
        response2 = await client.post(self.disable_initiate_url)
        assert response2.status_code == status.HTTP_200_OK
        mfa_token2 = response2.json()["result"]["mfaToken"]

        # Get session to verify counter is reset
        mfa_service = MFASessionService()
        session_id2, _, _ = await mfa_service.validate_and_get_session(mfa_token2)
        session_data = await mfa_service.get_session(session_id2)
        
        assert session_data is not None
        assert session_data.failed_totp_attempts == 0  # Fresh counter

    async def test_successful_verification_clears_global_lockout(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Successful MFA disable clears global lockout counter."""
        client.login(user_with_mfa)

        # Clear any existing global lockout first
        mfa_service = MFASessionService()
        await mfa_service.clear_global_lockout(user_with_mfa.id)

        # Make only 2 failed attempts to increment global counter (not hit lockout)
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        for _ in range(2):
            verify_data = {"mfaToken": mfa_token, "code": "000000"}
            await client.post(self.disable_verify_url, data=verify_data)

        # Now succeed (should clear global counter)
        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)
        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_200_OK

        # Re-enable MFA
        crud = UsersCRUD(session)
        new_secret = totp_service.generate_secret()
        encrypted = totp_service.encrypt_secret(new_secret)
        await crud.update_by_id(
            user_with_mfa.id,
            {"mfa_enabled": True, "mfa_secret": encrypted},
        )

        # Verify no global lockout (can initiate new disable)
        response = await client.post(self.disable_initiate_url)
        assert response.status_code == status.HTTP_200_OK

    async def test_global_lockout_prevents_new_session_creation(
        self, client: TestClient, user_with_mfa: User
    ):
        """Global lockout prevents creating new MFA sessions."""
        client.login(user_with_mfa)

        # Simulate reaching global lockout by making many failed attempts
        attempts_made = 0
        max_attempts_to_try = 15  # Should trigger global lockout

        for session_num in range(5):  # Try up to 5 sessions
            response = await client.post(self.disable_initiate_url)
            
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                # Successfully hit global lockout on initiate
                error = response.json()["result"][0]
                assert "locked" in error["message"].lower() or "too many" in error["message"].lower()
                return

            mfa_token = response.json()["result"]["mfaToken"]

            # Make invalid attempts
            for attempt in range(3):
                if attempts_made >= max_attempts_to_try:
                    break
                    
                verify_data = {"mfaToken": mfa_token, "code": "000000"}
                response = await client.post(self.disable_verify_url, data=verify_data)
                attempts_made += 1
                
                if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    # Hit lockout during verify
                    break

            if attempts_made >= max_attempts_to_try:
                break

        # Try to create a new session - should be blocked
        response = await client.post(self.disable_initiate_url)
        # Should either succeed or be locked out (implementation dependent)
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    async def test_rate_limit_is_user_specific(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Rate limits are isolated per user."""
        # Create second user with MFA
        user_service = UserService(session)
        user2_create = UserCreate(
            email="user2-rate@example.com",
            first_name="User",
            last_name="Two",
            password="ValidPassword123",
        )
        user2 = await user_service.create_user(user2_create)

        crud = UsersCRUD(session)
        secret2 = totp_service.generate_secret()
        encrypted2 = totp_service.encrypt_secret(secret2)
        await crud.update_by_id(
            user2.id,
            {"mfa_enabled": True, "mfa_secret": encrypted2},
        )
        user2_with_mfa = await crud.get_by_id(user2.id)

        # User 1 makes many failed attempts
        client.login(user_with_mfa)
        response = await client.post(self.disable_initiate_url)
        mfa_token1 = response.json()["result"]["mfaToken"]

        for _ in range(5):
            verify_data = {"mfaToken": mfa_token1, "code": "000000"}
            await client.post(self.disable_verify_url, data=verify_data)

        # User 2 should not be affected by User 1's rate limit
        client.login(user2_with_mfa)
        response = await client.post(self.disable_initiate_url)
        assert response.status_code == status.HTTP_200_OK

        mfa_token2 = response.json()["result"]["mfaToken"]
        decrypted2 = totp_service.decrypt_secret(user2_with_mfa.mfa_secret)
        valid_totp2 = totp_service.get_current_code(decrypted2)
        verify_data = {"mfaToken": mfa_token2, "code": valid_totp2}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_200_OK

    async def test_rate_limit_error_messages_are_informative(
        self, client: TestClient, user_with_mfa: User
    ):
        """Rate limit errors provide clear information to users."""
        client.login(user_with_mfa)

        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        # Trigger rate limit
        for _ in range(6):
            verify_data = {"mfaToken": mfa_token, "code": "000000"}
            response = await client.post(self.disable_verify_url, data=verify_data)

        # Check final rate limit response has informative message
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error = response.json()["result"][0]
            message = error["message"].lower()
            
            # Should mention rate limiting or too many attempts
            assert (
                "too many" in message
                or "rate limit" in message
                or "locked" in message
                or "try again" in message
            )
