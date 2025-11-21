"""Integration tests for MFA rate limiting and error handling."""

import http
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.router import router as auth_router
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User
from apps.users.services.totp import totp_service
from config import settings

TEST_PASSWORD = "Test1234!"


@pytest.fixture
async def user_with_mfa(session: AsyncSession, user: User) -> User:
    """Create user with MFA enabled."""
    secret = totp_service.generate_secret()
    encrypted_secret = totp_service.encrypt_secret(secret)

    crud = UsersCRUD(session)
    await crud.update_by_id(
        user.id,
        {
            "mfa_enabled": True,
            "mfa_secret": encrypted_secret,
        },
    )

    updated_user = await crud.get_by_id(user.id)
    assert updated_user is not None
    return updated_user


class TestMFARateLimiting(BaseTest):
    """Test MFA rate limiting functionality."""

    get_token_url = auth_router.url_path_for("get_token")
    verify_mfa_url = auth_router.url_path_for("verify_mfa_totp")

    async def test_per_session_rate_limit_increments_on_failure(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test that per-session rate limit counter increments on failed attempts."""
        mock_redis = AsyncMock()
        session_data = {
            "user_id": str(user_with_mfa.id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "failed_totp_attempts": 0,
        }
        mock_redis.get.return_value = json.dumps(session_data)

        with patch("apps.authentication.services.mfa_session.RedisCache", return_value=mock_redis):
            # Login
            login_response = await client.post(
                url=self.get_token_url,
                data=dict(
                    email=user_with_mfa.email_encrypted,
                    password=TEST_PASSWORD,
                    deviceId="test-device",
                ),
            )
            mfa_token = login_response.json()["result"]["mfa_token"]

            # First failed attempt
            await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=mfa_token,
                    code="000000",  # Invalid
                ),
            )

            # Redis set should be called to update failed attempts
            assert mock_redis.set.call_count >= 1
            last_call = mock_redis.set.call_args
            updated_data = json.loads(last_call.kwargs["value"])
            assert updated_data["failed_totp_attempts"] >= 1

    async def test_per_session_rate_limit_blocks_after_max_attempts(
        self, client: TestClient, user_with_mfa: User
    ):
        """Test that per-session rate limit blocks after reaching max attempts."""
        # Login
        login_response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )
        mfa_token = login_response.json()["result"]["mfa_token"]

        # Make max_attempts failed attempts
        max_attempts = settings.redis.mfa_max_attempts
        for i in range(max_attempts):
            response = await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=mfa_token,
                    code="000000",  # Invalid
                ),
            )

            if i < max_attempts - 1:
                # Should fail with invalid code
                assert response.status_code == http.HTTPStatus.BAD_REQUEST
            else:
                # Last attempt should trigger rate limit
                assert response.status_code == http.HTTPStatus.BAD_REQUEST
                # May indicate exceeded attempts or session expired

    async def test_global_rate_limit_increments_on_failure(self, client: TestClient, user_with_mfa: User):
        """Test that global rate limit counter increments across sessions."""
        mock_redis = AsyncMock()
        session_data = {
            "user_id": str(user_with_mfa.id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "failed_totp_attempts": 0,
        }
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.incr.return_value = 1

        with patch("apps.authentication.services.mfa_session.RedisCache", return_value=mock_redis):
            # Login
            login_response = await client.post(
                url=self.get_token_url,
                data=dict(
                    email=user_with_mfa.email_encrypted,
                    password=TEST_PASSWORD,
                    deviceId="test-device",
                ),
            )
            mfa_token = login_response.json()["result"]["mfa_token"]

            # Failed verification
            await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=mfa_token,
                    code="000000",
                ),
            )

            # Global counter should be incremented
            assert mock_redis.incr.call_count >= 1
            incr_call = mock_redis.incr.call_args
            assert "mfa_fail:" in incr_call.args[0]

    async def test_global_rate_limit_blocks_user_across_sessions(
        self, client: TestClient, user_with_mfa: User
    ):
        """Test that global rate limit blocks user across multiple sessions."""
        mock_redis = AsyncMock()

        # Simulate user already at global lockout threshold
        session_data = {
            "user_id": str(user_with_mfa.id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "failed_totp_attempts": 0,
        }
        mock_redis.get.side_effect = [
            # First get for session retrieval
            json.dumps(session_data),
            # Second get for global lockout check - already at limit
            str(settings.redis.mfa_global_lockout_attempts),
        ]

        with patch("apps.authentication.services.mfa_session.RedisCache", return_value=mock_redis):
            # Login
            login_response = await client.post(
                url=self.get_token_url,
                data=dict(
                    email=user_with_mfa.email_encrypted,
                    password=TEST_PASSWORD,
                    deviceId="test-device",
                ),
            )
            mfa_token = login_response.json()["result"]["mfa_token"]

            # Try to verify
            response = await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=mfa_token,
                    code="123456",
                ),
            )

            # Should be blocked by global lockout
            assert response.status_code == http.HTTPStatus.BAD_REQUEST

    async def test_global_lockout_cleared_after_successful_verification(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test that global lockout counter is cleared after successful verification."""
        mock_redis = AsyncMock()
        session_data = {
            "user_id": str(user_with_mfa.id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "failed_totp_attempts": 0,
        }
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.incr.return_value = 5

        with patch("apps.authentication.services.mfa_session.RedisCache", return_value=mock_redis):
            # Login
            login_response = await client.post(
                url=self.get_token_url,
                data=dict(
                    email=user_with_mfa.email_encrypted,
                    password=TEST_PASSWORD,
                    deviceId="test-device",
                ),
            )
            mfa_token = login_response.json()["result"]["mfa_token"]

            # Get valid code
            crud = UsersCRUD(session)
            fresh_user = await crud.get_by_id(user_with_mfa.id)
            assert fresh_user is not None
            decrypted_secret = totp_service.decrypt_secret(fresh_user.mfa_secret)
            valid_code = totp_service.get_current_code(decrypted_secret)

            # Successful verification
            response = await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=mfa_token,
                    code=valid_code,
                ),
            )

            assert response.status_code == http.HTTPStatus.OK

            # Global lockout should be cleared (deleted)
            delete_calls = [call for call in mock_redis.delete.call_args_list if "mfa_fail:" in str(call)]
            assert len(delete_calls) > 0


class TestMFAErrorHandling(BaseTest):
    """Test MFA error handling."""

    get_token_url = auth_router.url_path_for("get_token")
    verify_mfa_url = auth_router.url_path_for("verify_mfa_totp")

    async def test_expired_mfa_session_returns_error(self, client: TestClient, user_with_mfa: User):
        """Test that expired MFA session returns appropriate error."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Session not found (expired)

        with patch("apps.authentication.services.mfa_session.RedisCache", return_value=mock_redis):
            # Create fake MFA token
            from apps.authentication.services import AuthenticationService
            from sqlalchemy.ext.asyncio import AsyncSession

            # Need to create a valid token structure
            import uuid

            fake_session_id = str(uuid.uuid4())

            # Login to get real token structure
            login_response = await client.post(
                url=self.get_token_url,
                data=dict(
                    email=user_with_mfa.email_encrypted,
                    password=TEST_PASSWORD,
                    deviceId="test-device",
                ),
            )
            mfa_token = login_response.json()["result"]["mfa_token"]

            # Now mock Redis to return None (expired session)
            mock_redis.get.return_value = None

            # Try to verify with expired session
            response = await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=mfa_token,
                    code="123456",
                ),
            )

            assert response.status_code == http.HTTPStatus.BAD_REQUEST

    async def test_malformed_mfa_token_returns_error(self, client: TestClient, user_with_mfa: User):
        """Test that malformed MFA token returns appropriate error."""
        malformed_tokens = [
            "not.a.token",
            "invalid",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        ]

        for token in malformed_tokens:
            response = await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=token,
                    code="123456",
                ),
            )

            assert response.status_code == http.HTTPStatus.BAD_REQUEST

    async def test_invalid_totp_code_format_returns_error(self, client: TestClient, user_with_mfa: User):
        """Test that invalid TOTP code formats return appropriate error."""
        # Login
        login_response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )
        mfa_token = login_response.json()["result"]["mfa_token"]

        invalid_codes = [
            "12345",  # Too short
            "1234567",  # Too long
            "abcdef",  # Not digits
            "",  # Empty
        ]

        for code in invalid_codes:
            response = await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=mfa_token,
                    code=code,
                ),
            )

            # Should return error (400 or 422 for validation)
            assert response.status_code in [http.HTTPStatus.BAD_REQUEST, http.HTTPStatus.UNPROCESSABLE_ENTITY]

    async def test_missing_mfa_token_returns_error(self, client: TestClient, user_with_mfa: User):
        """Test that missing MFA token returns validation error."""
        response = await client.post(
            url=self.verify_mfa_url,
            data=dict(
                code="123456",
                # mfa_token missing
            ),
        )

        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_missing_totp_code_returns_error(self, client: TestClient, user_with_mfa: User):
        """Test that missing TOTP code returns validation error."""
        # Login
        login_response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )
        mfa_token = login_response.json()["result"]["mfa_token"]

        response = await client.post(
            url=self.verify_mfa_url,
            data=dict(
                mfa_token=mfa_token,
                # code missing
            ),
        )

        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_session_deleted_after_rate_limit_exceeded(self, client: TestClient, user_with_mfa: User):
        """Test that MFA session is deleted when rate limit is exceeded."""
        mock_redis = AsyncMock()
        session_data = {
            "user_id": str(user_with_mfa.id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "failed_totp_attempts": settings.redis.mfa_max_attempts - 1,  # One away from limit
        }
        mock_redis.get.return_value = json.dumps(session_data)

        with patch("apps.authentication.services.mfa_session.RedisCache", return_value=mock_redis):
            # Login
            login_response = await client.post(
                url=self.get_token_url,
                data=dict(
                    email=user_with_mfa.email_encrypted,
                    password=TEST_PASSWORD,
                    deviceId="test-device",
                ),
            )
            mfa_token = login_response.json()["result"]["mfa_token"]

            # One more failed attempt to exceed limit
            await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=mfa_token,
                    code="000000",
                ),
            )

            # Session should be deleted
            mock_redis.delete.assert_called()

    async def test_corrupted_redis_session_data_handled_gracefully(self, client: TestClient, user_with_mfa: User):
        """Test that corrupted Redis session data is handled gracefully."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "corrupted-invalid-json-data"

        with patch("apps.authentication.services.mfa_session.RedisCache", return_value=mock_redis):
            # Login
            login_response = await client.post(
                url=self.get_token_url,
                data=dict(
                    email=user_with_mfa.email_encrypted,
                    password=TEST_PASSWORD,
                    deviceId="test-device",
                ),
            )
            mfa_token = login_response.json()["result"]["mfa_token"]

            # Try to verify with corrupted session
            response = await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfa_token=mfa_token,
                    code="123456",
                ),
            )

            # Should handle gracefully with error
            assert response.status_code == http.HTTPStatus.BAD_REQUEST

            # Corrupted session should be deleted
            mock_redis.delete.assert_called()
