"""Integration tests for MFA authentication flow (simplified)."""

import http
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.router import router as auth_router
from apps.authentication.services import AuthenticationService
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User
from apps.users.services.totp import totp_service

TEST_PASSWORD = "Test1234!"


@pytest.fixture
async def user_with_mfa(session: AsyncSession, user: User) -> User:
    """Create user with MFA enabled."""
    # Generate and encrypt TOTP secret
    secret = totp_service.generate_secret()
    encrypted_secret = totp_service.encrypt_secret(secret)

    # Enable MFA for user
    crud = UsersCRUD(session)
    await crud.update_by_id(
        user.id,
        {
            "mfa_enabled": True,
            "mfa_secret": encrypted_secret,
        },  # type: ignore[arg-type]
    )

    # Refresh user
    updated_user = await crud.get_by_id(user.id)
    assert updated_user is not None
    assert updated_user.mfa_enabled is True
    assert updated_user.mfa_secret is not None

    return updated_user


@pytest.fixture
async def user_without_mfa(session: AsyncSession, user: User) -> User:
    """Ensure user has MFA disabled."""
    crud = UsersCRUD(session)
    await crud.update_by_id(
        user.id,
        {
            "mfa_enabled": False,
            "mfa_secret": None,
        },  # type: ignore[arg-type]
    )

    updated_user = await crud.get_by_id(user.id)
    assert updated_user is not None
    assert updated_user.mfa_enabled is False
    assert updated_user.mfa_secret is None

    return updated_user


class TestMFALoginFlow(BaseTest):
    """Test MFA login flow integration."""

    get_token_url = auth_router.url_path_for("get_token")
    verify_mfa_url = auth_router.url_path_for("verify_mfa_totp")

    async def test_login_without_mfa_returns_tokens_directly(self, client: TestClient, user_without_mfa: User):
        """Test that login without MFA enabled returns tokens immediately."""
        response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_without_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]

        # Should have user and token
        assert "user" in data
        assert "token" in data
        assert data["user"]["id"] == str(user_without_mfa.id)

        # Should NOT have MFA fields (camelCase)
        assert "mfaRequired" not in data
        assert "mfaSessionId" not in data
        assert "mfaToken" not in data

    async def test_login_with_mfa_returns_mfa_required(self, client: TestClient, user_with_mfa: User):
        """Test that login with MFA enabled returns MFA required response."""
        response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        raw_json = response.json()
        data = raw_json["result"]

        # Should indicate MFA is required (camelCase)
        assert data["mfaRequired"] is True
        assert "mfaSessionId" in data
        assert "mfaToken" in data

        # Should NOT have user or regular tokens yet
        assert "user" not in data
        assert "token" not in data

        # MFA session ID should be valid UUID format
        import uuid

        uuid.UUID(data["mfaSessionId"])  # validates format

    async def test_login_with_mfa_creates_redis_session(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test that MFA login creates session in Redis."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Session doesn't exist yet

        with patch("apps.authentication.services.mfa_session.RedisCache", return_value=mock_redis):
            response = await client.post(
                url=self.get_token_url,
                data=dict(
                    email=user_with_mfa.email_encrypted,
                    password=TEST_PASSWORD,
                    deviceId="test-device",
                ),
            )

            assert response.status_code == http.HTTPStatus.OK

            # Redis set should have been called to create session
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args

            # Verify session data structure
            stored_data = json.loads(call_args.kwargs["value"])
            assert stored_data["user_id"] == str(user_with_mfa.id)
            assert stored_data["failed_totp_attempts"] == 0
            assert "created_at" in stored_data

            # Verify TTL is set (5 minutes)
            assert call_args.kwargs["ex"] == 300

    async def test_login_with_mfa_token_contains_session_id(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test that MFA token contains session ID in payload."""
        response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]

        mfa_token = data["mfaToken"]
        mfa_session_id = data["mfaSessionId"]

        # Decode token and verify it contains session ID
        auth_service = AuthenticationService(session)
        decoded_session_id = auth_service.decode_mfa_token(mfa_token)

        assert decoded_session_id == mfa_session_id

    async def test_login_with_wrong_credentials_no_mfa_session(self, client: TestClient, user_with_mfa: User):
        """Test that wrong password doesn't create MFA session."""
        mock_redis = AsyncMock()

        with patch("apps.authentication.services.mfa_session.RedisCache", return_value=mock_redis):
            response = await client.post(
                url=self.get_token_url,
                data=dict(
                    email=user_with_mfa.email_encrypted,
                    password="WrongPassword123!",
                    deviceId="test-device",
                ),
            )

            # Should fail authentication (Unauthorized)
            assert response.status_code == http.HTTPStatus.UNAUTHORIZED

            # Should NOT create MFA session
            mock_redis.set.assert_not_called()


class TestMFATOTPVerification(BaseTest):
    """Test MFA TOTP verification integration."""

    get_token_url = auth_router.url_path_for("get_token")
    verify_mfa_url = auth_router.url_path_for("verify_mfa_totp")

    async def test_verify_mfa_with_valid_code_returns_tokens(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test successful MFA verification returns access and refresh tokens."""
        # Step 1: Login to get MFA token
        login_response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )
        login_data = login_response.json()["result"]
        mfa_token = login_data["mfaToken"]

        # Step 2: Get valid TOTP code
        crud = UsersCRUD(session)
        fresh_user = await crud.get_by_id(user_with_mfa.id)
        assert fresh_user is not None
        assert fresh_user.mfa_secret is not None
        decrypted_secret = totp_service.decrypt_secret(fresh_user.mfa_secret)
        valid_code = totp_service.get_current_code(decrypted_secret)

        # Step 3: Verify TOTP
        verify_response = await client.post(
            url=self.verify_mfa_url,
            data=dict(
                mfaToken=mfa_token,
                totpCode=valid_code,
            ),
        )

        assert verify_response.status_code == http.HTTPStatus.OK
        verify_data = verify_response.json()["result"]

        # Should have user and tokens
        assert "user" in verify_data
        assert "token" in verify_data
        assert verify_data["user"]["id"] == str(user_with_mfa.id)

        # Should have access and refresh tokens
        assert "accessToken" in verify_data["token"]
        assert "refreshToken" in verify_data["token"]

    async def test_verify_mfa_with_invalid_code_fails(self, client: TestClient, user_with_mfa: User):
        """Test that invalid TOTP code fails verification."""
        # Step 1: Login to get MFA token
        login_response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )
        login_data = login_response.json()["result"]
        mfa_token = login_data["mfaToken"]

        # Step 2: Try with invalid code
        verify_response = await client.post(
            url=self.verify_mfa_url,
            data=dict(
                mfaToken=mfa_token,
                totpCode="000000",  # Invalid code
            ),
        )

        # Invalid TOTP code keeps user unauthenticated, expect 401 Unauthorized
        assert verify_response.status_code == http.HTTPStatus.UNAUTHORIZED
        error_data = verify_response.json()

        # Should indicate invalid TOTP code
        assert (
            "Invalid TOTP" in error_data["result"][0]["message"] or "Invalid code" in error_data["result"][0]["message"]
        )

    async def test_verify_mfa_with_invalid_token_fails(self, client: TestClient, user_with_mfa: User):
        """Test that invalid MFA token fails verification."""
        verify_response = await client.post(
            url=self.verify_mfa_url,
            data=dict(
                mfaToken="invalid.token.here",
                totpCode="123456",
            ),
        )

        # Invalid token should yield Unauthorized (401)
        assert verify_response.status_code == http.HTTPStatus.UNAUTHORIZED

    async def test_verify_mfa_updates_last_totp_time_step(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test that successful MFA verification updates last_totp_time_step."""
        # Get initial time step (should be None)
        crud = UsersCRUD(session)
        initial_user = await crud.get_by_id(user_with_mfa.id)
        assert initial_user is not None
        initial_time_step = initial_user.last_totp_time_step

        # Login and verify
        login_response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )
        mfa_token = login_response.json()["result"]["mfaToken"]

        assert initial_user.mfa_secret is not None
        decrypted_secret = totp_service.decrypt_secret(initial_user.mfa_secret)
        valid_code = totp_service.get_current_code(decrypted_secret)

        verify_response = await client.post(
            url=self.verify_mfa_url,
            data=dict(
                mfaToken=mfa_token,
                totpCode=valid_code,
            ),
        )

        assert verify_response.status_code == http.HTTPStatus.OK

        # Check that time step was updated
        updated_user = await crud.get_by_id(user_with_mfa.id)
        assert updated_user is not None
        assert updated_user.last_totp_time_step is not None
        assert updated_user.last_totp_time_step > (initial_time_step or 0)

    async def test_verify_mfa_deletes_session_after_success(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test that MFA session is deleted after successful verification."""
        mock_redis = AsyncMock()

        # Mock session data
        session_data = {
            "user_id": str(user_with_mfa.id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "failed_totp_attempts": 0,
        }
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.incr.return_value = 0

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
            mfa_token = login_response.json()["result"]["mfaToken"]

            # Get valid code
            crud = UsersCRUD(session)
            fresh_user = await crud.get_by_id(user_with_mfa.id)
            assert fresh_user is not None
            assert fresh_user.mfa_secret is not None
            decrypted_secret = totp_service.decrypt_secret(fresh_user.mfa_secret)
            valid_code = totp_service.get_current_code(decrypted_secret)

            # Verify
            verify_response = await client.post(
                url=self.verify_mfa_url,
                data=dict(
                    mfaToken=mfa_token,
                    totpCode=valid_code,
                ),
            )

            assert verify_response.status_code == http.HTTPStatus.OK

            # Session should be deleted
            mock_redis.delete.assert_called()


class TestMFAReplayProtection(BaseTest):
    """Test TOTP replay protection."""

    get_token_url = auth_router.url_path_for("get_token")
    verify_mfa_url = auth_router.url_path_for("verify_mfa_totp")

    async def test_replay_attack_same_code_twice_fails(
        self, client: TestClient, user_with_mfa: User, session: AsyncSession
    ):
        """Test that using the same code twice within same time window fails."""
        # First successful verification
        login_response = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device",
            ),
        )
        mfa_token = login_response.json()["result"]["mfaToken"]

        crud = UsersCRUD(session)
        fresh_user = await crud.get_by_id(user_with_mfa.id)
        assert fresh_user is not None
        assert fresh_user.mfa_secret is not None
        decrypted_secret = totp_service.decrypt_secret(fresh_user.mfa_secret)
        valid_code = totp_service.get_current_code(decrypted_secret)

        first_verify = await client.post(
            url=self.verify_mfa_url,
            data=dict(
                mfaToken=mfa_token,
                totpCode=valid_code,
            ),
        )
        assert first_verify.status_code == http.HTTPStatus.OK

        # Try to reuse the same code (replay attack)
        login_response_2 = await client.post(
            url=self.get_token_url,
            data=dict(
                email=user_with_mfa.email_encrypted,
                password=TEST_PASSWORD,
                deviceId="test-device-2",
            ),
        )
        mfa_token_2 = login_response_2.json()["result"]["mfaToken"]

        # Try same code again
        second_verify = await client.post(
            url=self.verify_mfa_url,
            data=dict(
                mfaToken=mfa_token_2,
                totpCode=valid_code,  # Same code
            ),
        )

        # Should fail due to replay protection (401 Unauthorized - invalid/reused code)
        assert second_verify.status_code == http.HTTPStatus.UNAUTHORIZED
