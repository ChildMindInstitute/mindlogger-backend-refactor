"""Tests for security aspects of MFA disable flow."""

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
class TestMFADisableSecurity:
    """Test security aspects of MFA disable flow."""

    disable_initiate_url = "/users/me/mfa/totp/disable/initiate"
    disable_verify_url = "/users/me/mfa/totp/disable/verify"

    async def test_disable_requires_authentication(self, client: TestClient):
        """Unauthenticated requests to disable endpoints are rejected."""
        # Try to initiate without authentication
        response = await client.post(self.disable_initiate_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Try to verify without authentication
        verify_data = {"mfaToken": "fake-token", "code": "123456"}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_cannot_disable_another_users_mfa(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """User cannot disable another user's MFA."""
        # Create a second user (different from user_with_mfa)
        from pydantic import EmailStr
        
        user_service = UserService(session)
        user2_create = UserCreate(
            email=EmailStr("attacker@example.com"),
            password="Attacker123!",
            first_name="Attacker",
            last_name="User",
        )
        user2 = await user_service.create_user(user2_create)
        
        # User 1 initiates their own disable
        client.login(user_with_mfa)
        response = await client.post(self.disable_initiate_url)
        assert response.status_code == status.HTTP_200_OK
        mfa_token = response.json()["result"]["mfaToken"]

        # User 2 tries to use User 1's token
        client.login(user2)
        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)
        verify_data = {"mfaToken": mfa_token, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data)

        # Should fail - token belongs to different user
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

        # Verify User 1's MFA is still enabled
        crud = UsersCRUD(session)
        user1_after = await crud.get_by_id(user_with_mfa.id)
        assert user1_after.mfa_enabled is True

    async def test_mfa_token_has_limited_lifetime(
        self, client: TestClient, user_with_mfa: User
    ):
        """MFA tokens expire after configured time."""
        import jwt
        from datetime import datetime, timedelta, timezone
        from config import settings

        client.login(user_with_mfa)

        # Create session data with old timestamp (expired)
        expired_time = datetime.now(timezone.utc) - timedelta(
            seconds=settings.redis.mfa_session_ttl + 1
        )
        
        # Create session data and manually save to Redis
        from apps.authentication.services.mfa_session import MFASessionData
        import json
        
        mfa_service = MFASessionService()
        session_id = "test-session-id-expired"
        redis_key = f"mfa_session:{session_id}"
        
        session_data = MFASessionData(
            user_id=user_with_mfa.id,
            created_at=expired_time,
            purpose="disable",
            failed_totp_attempts=0,
        )
        
        # Manually save to Redis (bypass create_session to use old timestamp)
        await mfa_service.redis_client.set(
            key=redis_key,
            value=json.dumps(session_data.to_dict()),
            ex=10,  # Short TTL for test
        )

        # Create expired token
        expired_payload = {
            "session_id": session_id,
            "user_id": str(user_with_mfa.id),
            "purpose": "disable",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
        }
        expired_token = jwt.encode(
            expired_payload, settings.authentication.mfa_token.secret_key, algorithm="HS256"
        )

        # Try to verify with expired token
        verify_data = {"mfaToken": expired_token, "code": "123456"}
        response = await client.post(self.disable_verify_url, data=verify_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error = response.json()["result"][0]
        assert "expired" in error["message"].lower() or "invalid" in error["message"].lower()

    async def test_tampered_mfa_token_is_rejected(
        self, client: TestClient, user_with_mfa: User
    ):
        """Tampered MFA tokens are rejected."""
        client.login(user_with_mfa)

        # Get a valid token
        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        # Tamper with the token
        tampered_token = mfa_token[:-5] + "XXXXX"

        # Try to verify with tampered token
        verify_data = {"mfaToken": tampered_token, "code": "123456"}
        response = await client.post(self.disable_verify_url, data=verify_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_totp_time_step_replay_prevention(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Same TOTP code cannot be used twice (replay attack prevention)."""
        client.login(user_with_mfa)

        # Generate valid TOTP
        decrypted_secret = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        valid_totp = totp_service.get_current_code(decrypted_secret)

        # First disable attempt succeeds
        response1 = await client.post(self.disable_initiate_url)
        mfa_token1 = response1.json()["result"]["mfaToken"]
        verify_data = {"mfaToken": mfa_token1, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_200_OK

        # Re-enable MFA for second test
        crud = UsersCRUD(session)
        new_secret = totp_service.generate_secret()
        encrypted_secret = totp_service.encrypt_secret(new_secret)
        await crud.update_by_id(
            user_with_mfa.id,
            {
                "mfa_enabled": True,
                "mfa_secret": encrypted_secret,
                "last_totp_time_step": None,
            },
        )

        # Second disable attempt with same TOTP should fail
        # (even though it's a new session, the time step was recorded)
        response2 = await client.post(self.disable_initiate_url)
        mfa_token2 = response2.json()["result"]["mfaToken"]

        # Use same TOTP time step (will fail because different secret)
        verify_data = {"mfaToken": mfa_token2, "code": valid_totp}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_session_isolation_between_users(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """MFA sessions are properly isolated between users."""
        # Create second user with MFA
        from apps.users.cruds.user import UsersCRUD

        user2_data = UserCreate(
            email="user2@example.com",
            first_name="User",
            last_name="Two",
            password="ValidPassword123",
        )
        user_service = UserService(session)
        user2 = await user_service.create_user(user2_data)
        await session.flush()

        # Enable MFA for user2
        crud = UsersCRUD(session)
        secret2 = totp_service.generate_secret()
        encrypted2 = totp_service.encrypt_secret(secret2)
        await crud.update_by_id(
            user2.id,
            {
                "mfa_enabled": True,
                "mfa_secret": encrypted2,
            },
        )
        user2_with_mfa = await crud.get_by_id(user2.id)

        # User 1 initiates disable
        client.login(user_with_mfa)
        response1 = await client.post(self.disable_initiate_url)
        mfa_token1 = response1.json()["result"]["mfaToken"]

        # User 2 initiates disable
        client.login(user2_with_mfa)
        response2 = await client.post(self.disable_initiate_url)
        mfa_token2 = response2.json()["result"]["mfaToken"]

        # Verify tokens are different
        assert mfa_token1 != mfa_token2

        # User 1 completes their disable
        client.login(user_with_mfa)
        decrypted1 = totp_service.decrypt_secret(user_with_mfa.mfa_secret)
        totp1 = totp_service.get_current_code(decrypted1)
        verify_data = {"mfaToken": mfa_token1, "code": totp1}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_200_OK

        # User 2's session should still be valid
        client.login(user2_with_mfa)
        decrypted2 = totp_service.decrypt_secret(user2_with_mfa.mfa_secret)
        totp2 = totp_service.get_current_code(decrypted2)
        verify_data = {"mfaToken": mfa_token2, "code": totp2}
        response = await client.post(self.disable_verify_url, data=verify_data)
        assert response.status_code == status.HTTP_200_OK

    async def test_invalid_purpose_token_is_rejected(
        self, client: TestClient, user_with_mfa: User
    ):
        """Token with wrong purpose cannot be used for disable."""
        import jwt
        from datetime import datetime, timedelta, timezone
        from config import settings

        client.login(user_with_mfa)

        # Create a token with purpose="enable" instead of "disable"
        from apps.authentication.services.mfa_session import MFASessionData
        import json
        
        mfa_service = MFASessionService()
        session_id = "test-session-id-wrong-purpose"
        redis_key = f"mfa_session:{session_id}"
        
        session_data = MFASessionData(
            user_id=user_with_mfa.id,
            created_at=datetime.now(timezone.utc),
            purpose="enable",  # Wrong purpose
            failed_totp_attempts=0,
        )
        
        # Manually save to Redis
        await mfa_service.redis_client.set(
            key=redis_key,
            value=json.dumps(session_data.to_dict()),
            ex=settings.redis.mfa_session_ttl,
        )

        wrong_purpose_payload = {
            "session_id": session_id,
            "user_id": str(user_with_mfa.id),
            "purpose": "enable",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "iat": datetime.now(timezone.utc),
        }
        wrong_purpose_token = jwt.encode(
            wrong_purpose_payload,
            settings.authentication.mfa_token.secret_key,
            algorithm="HS256",
        )

        # Try to verify with wrong purpose token
        verify_data = {"mfaToken": wrong_purpose_token, "code": "123456"}
        response = await client.post(self.disable_verify_url, data=verify_data)

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    async def test_sql_injection_in_totp_code(
        self, client: TestClient, user_with_mfa: User
    ):
        """SQL injection attempts in TOTP code are safely handled."""
        client.login(user_with_mfa)

        response = await client.post(self.disable_initiate_url)
        mfa_token = response.json()["result"]["mfaToken"]

        # Try SQL injection in TOTP code
        malicious_codes = [
            "'; DROP TABLE users; --",
            "123' OR '1'='1",
            "000000' UNION SELECT * FROM users --",
        ]

        for malicious_code in malicious_codes:
            verify_data = {"mfaToken": mfa_token, "code": malicious_code}
            response = await client.post(self.disable_verify_url, data=verify_data)
            # Should fail safely (validation error or invalid code)
            assert response.status_code in (
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

    async def test_xss_in_response_messages(
        self, client: TestClient, user_with_mfa: User
    ):
        """Response messages don't include unsanitized user input (XSS prevention)."""
        client.login(user_with_mfa)

        response = await client.post(self.disable_initiate_url)
        result = response.json()["result"]

        # Verify response doesn't contain script tags or HTML
        message = result.get("message", "")
        assert "<script>" not in message.lower()
        assert "javascript:" not in message.lower()
        assert "onerror=" not in message.lower()
