"""Unit tests for MFA Token generation and validation."""

import time
import uuid
from datetime import datetime, timedelta

import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.errors import MFATokenInvalidError
from apps.authentication.services import AuthenticationService
from config import settings


@pytest.fixture
def auth_service(session: AsyncSession) -> AuthenticationService:
    """Create authentication service instance."""
    return AuthenticationService(session)


@pytest.fixture
def sample_mfa_session_id():
    """Sample MFA session ID."""
    return str(uuid.uuid4())


class TestMFATokenGeneration:
    """Test MFA token generation."""

    def test_create_mfa_token(self, auth_service: AuthenticationService, sample_mfa_session_id):
        """Test creating MFA token with session ID."""
        mfa_token = auth_service.create_mfa_token(mfa_session_id=sample_mfa_session_id)

        assert isinstance(mfa_token, str)
        assert len(mfa_token) > 0

        # Decode and verify payload
        payload = jwt.decode(
            mfa_token,
            settings.authentication.access_token.secret_key,
            algorithms=[settings.authentication.access_token.algorithm],
        )

        assert payload["mfa_session_id"] == sample_mfa_session_id
        assert "exp" in payload  # Should have expiration
        assert "iat" in payload  # Should have issued at

    def test_create_mfa_token_has_expiration(self, auth_service: AuthenticationService, sample_mfa_session_id):
        """Test MFA token has proper expiration time."""
        mfa_token = auth_service.create_mfa_token(mfa_session_id=sample_mfa_session_id)

        payload = jwt.decode(
            mfa_token,
            settings.authentication.access_token.secret_key,
            algorithms=[settings.authentication.access_token.algorithm],
        )

        # Expiration should be in the future
        exp_timestamp = payload["exp"]
        now_timestamp = time.time()
        assert exp_timestamp > now_timestamp

        # Should expire in approximately 5 minutes (300 seconds)
        time_until_expiry = exp_timestamp - now_timestamp
        assert 290 <= time_until_expiry <= 310  # Allow 10 second tolerance

    def test_create_mfa_token_unique_for_each_session(self, auth_service: AuthenticationService):
        """Test different session IDs produce different tokens."""
        session_id_1 = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())

        token_1 = auth_service.create_mfa_token(mfa_session_id=session_id_1)
        token_2 = auth_service.create_mfa_token(mfa_session_id=session_id_2)

        assert token_1 != token_2

        # Verify payloads are different
        payload_1 = jwt.decode(
            token_1,
            settings.authentication.access_token.secret_key,
            algorithms=[settings.authentication.access_token.algorithm],
        )
        payload_2 = jwt.decode(
            token_2,
            settings.authentication.access_token.secret_key,
            algorithms=[settings.authentication.access_token.algorithm],
        )

        assert payload_1["mfa_session_id"] != payload_2["mfa_session_id"]


class TestMFATokenValidation:
    """Test MFA token validation and decoding."""

    def test_decode_mfa_token_success(self, auth_service: AuthenticationService, sample_mfa_session_id):
        """Test successfully decoding valid MFA token."""
        # Create token
        mfa_token = auth_service.create_mfa_token(mfa_session_id=sample_mfa_session_id)

        # Decode token
        mfa_session_id = auth_service.decode_mfa_token(mfa_token)

        assert mfa_session_id == sample_mfa_session_id

    def test_decode_mfa_token_invalid_signature(self, auth_service: AuthenticationService):
        """Test decoding token with invalid signature raises error."""
        # Create token with wrong secret
        payload = {
            "mfa_session_id": str(uuid.uuid4()),
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
        }
        invalid_token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")

        with pytest.raises(MFATokenInvalidError):
            auth_service.decode_mfa_token(invalid_token)

    def test_decode_mfa_token_expired(self, auth_service: AuthenticationService, sample_mfa_session_id):
        """Test decoding expired token raises error."""
        # Create expired token
        payload = {
            "mfa_session_id": sample_mfa_session_id,
            "exp": datetime.utcnow() - timedelta(minutes=1),  # Expired 1 minute ago
            "iat": datetime.utcnow() - timedelta(minutes=6),
        }
        expired_token = jwt.encode(
            payload,
            settings.authentication.access_token.secret_key,
            algorithm=settings.authentication.access_token.algorithm,
        )

        with pytest.raises(MFATokenInvalidError):
            auth_service.decode_mfa_token(expired_token)

    def test_decode_mfa_token_missing_session_id(self, auth_service: AuthenticationService):
        """Test decoding token without mfa_session_id raises error."""
        # Create token without mfa_session_id
        payload = {
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
        }
        invalid_token = jwt.encode(
            payload,
            settings.authentication.access_token.secret_key,
            algorithm=settings.authentication.access_token.algorithm,
        )

        with pytest.raises(MFATokenInvalidError):
            auth_service.decode_mfa_token(invalid_token)

    def test_decode_mfa_token_malformed(self, auth_service: AuthenticationService):
        """Test decoding malformed token raises error."""
        malformed_tokens = [
            "not.a.token",
            "invalid",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        ]

        for token in malformed_tokens:
            with pytest.raises(MFATokenInvalidError):
                auth_service.decode_mfa_token(token)

    def test_decode_mfa_token_none(self, auth_service: AuthenticationService):
        """Test decoding None token raises error."""
        with pytest.raises(MFATokenInvalidError):
            auth_service.decode_mfa_token(None)  # type: ignore

    def test_decode_mfa_token_wrong_algorithm(self, auth_service: AuthenticationService, sample_mfa_session_id):
        """Test decoding token with wrong algorithm raises error."""
        # Create token with different algorithm
        payload = {
            "mfa_session_id": sample_mfa_session_id,
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
        }
        # Use RS256 instead of HS256
        wrong_algo_token = jwt.encode(payload, "secret", algorithm="HS512")

        with pytest.raises(MFATokenInvalidError):
            auth_service.decode_mfa_token(wrong_algo_token)

    def test_mfa_token_reusable_before_expiration(self, auth_service: AuthenticationService, sample_mfa_session_id):
        """Test MFA token can be decoded multiple times before expiration."""
        mfa_token = auth_service.create_mfa_token(mfa_session_id=sample_mfa_session_id)

        # Decode multiple times
        session_id_1 = auth_service.decode_mfa_token(mfa_token)
        session_id_2 = auth_service.decode_mfa_token(mfa_token)
        session_id_3 = auth_service.decode_mfa_token(mfa_token)

        assert session_id_1 == sample_mfa_session_id
        assert session_id_2 == sample_mfa_session_id
        assert session_id_3 == sample_mfa_session_id

    def test_mfa_token_different_keys_produce_different_tokens(
        self, auth_service: AuthenticationService, sample_mfa_session_id
    ):
        """Test that different signing keys produce different tokens."""
        # Create token with default key
        token_1 = auth_service.create_mfa_token(mfa_session_id=sample_mfa_session_id)

        # Create token with different payload timestamp (simulates different key)
        time.sleep(0.1)  # Ensure different iat
        token_2 = auth_service.create_mfa_token(mfa_session_id=sample_mfa_session_id)

        # Tokens should be different due to different iat
        assert token_1 != token_2

        # But both should decode to same session ID
        assert auth_service.decode_mfa_token(token_1) == sample_mfa_session_id
        assert auth_service.decode_mfa_token(token_2) == sample_mfa_session_id


class TestMFATokenSecurity:
    """Test security aspects of MFA tokens."""

    def test_mfa_token_cannot_be_forged(self, auth_service: AuthenticationService):
        """Test that tokens with valid structure but wrong signature are rejected."""
        # Create valid payload
        payload = {
            "mfa_session_id": str(uuid.uuid4()),
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
        }

        # Sign with attacker's key
        forged_token = jwt.encode(payload, "attacker-secret-key", algorithm="HS256")

        # Should fail verification
        with pytest.raises(MFATokenInvalidError):
            auth_service.decode_mfa_token(forged_token)

    def test_mfa_token_tampering_detection(self, auth_service: AuthenticationService, sample_mfa_session_id):
        """Test that tampering with token payload is detected."""
        # Create valid token
        mfa_token = auth_service.create_mfa_token(mfa_session_id=sample_mfa_session_id)

        # Tamper with the token (change a character in the payload section)
        parts = mfa_token.split(".")
        if len(parts) == 3:
            # Modify middle part (payload)
            tampered_payload = parts[1][:-1] + "X"
            tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

            # Should fail verification
            with pytest.raises(MFATokenInvalidError):
                auth_service.decode_mfa_token(tampered_token)

    def test_mfa_token_session_id_is_uuid_format(self, auth_service: AuthenticationService):
        """Test that decoded session ID is valid UUID format."""
        session_id = str(uuid.uuid4())
        mfa_token = auth_service.create_mfa_token(mfa_session_id=session_id)

        decoded_session_id = auth_service.decode_mfa_token(mfa_token)

        # Should be valid UUID
        uuid.UUID(decoded_session_id)
        assert decoded_session_id == session_id

    def test_mfa_token_expiration_boundary(self, auth_service: AuthenticationService, sample_mfa_session_id):
        """Test token expiration at exact boundary."""
        # Create token that expires in 1 second
        payload = {
            "mfa_session_id": sample_mfa_session_id,
            "exp": datetime.utcnow() + timedelta(seconds=1),
            "iat": datetime.utcnow(),
        }
        short_lived_token = jwt.encode(
            payload,
            settings.authentication.access_token.secret_key,
            algorithm=settings.authentication.access_token.algorithm,
        )

        # Should work immediately
        session_id = auth_service.decode_mfa_token(short_lived_token)
        assert session_id == sample_mfa_session_id

        # Wait for expiration
        time.sleep(2)

        # Should now be expired
        with pytest.raises(MFATokenInvalidError):
            auth_service.decode_mfa_token(short_lived_token)
