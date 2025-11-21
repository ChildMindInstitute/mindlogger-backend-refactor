"""Unit tests for MFA Session Service."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.authentication.services.mfa_session import MFASessionData, MFASessionService
from config import settings


@pytest.fixture(autouse=True)
def mock_logger(mocker):
    """Mock logger for all tests to avoid logging issues."""
    return mocker.patch("apps.authentication.services.mfa_session.logger")


@pytest.fixture
def mfa_service():
    """Create MFA session service instance for testing."""
    return MFASessionService()


@pytest.fixture
def mock_redis(mocker):
    """Mock Redis client."""
    mock_redis = AsyncMock()
    mocker.patch(
        "apps.authentication.services.mfa_session.RedisCache",
        return_value=mock_redis,
    )
    return mock_redis


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_session_data(sample_user_id):
    """Sample session data."""
    return MFASessionData(
        user_id=sample_user_id,
        created_at=datetime.now(timezone.utc),
        failed_totp_attempts=0,
    )


class TestMFASessionData:
    """Test MFASessionData class."""

    def test_to_dict(self, sample_session_data, sample_user_id):
        """Test converting session data to dictionary."""
        data_dict = sample_session_data.to_dict()

        assert data_dict["user_id"] == str(sample_user_id)
        assert "created_at" in data_dict
        assert data_dict["failed_totp_attempts"] == 0

    def test_from_dict(self, sample_user_id):
        """Test creating session data from dictionary."""
        created_at = datetime.now(timezone.utc)
        data_dict = {
            "user_id": str(sample_user_id),
            "created_at": created_at.isoformat(),
            "failed_totp_attempts": 2,
        }

        session_data = MFASessionData.from_dict(data_dict)

        assert session_data.user_id == sample_user_id
        assert isinstance(session_data.created_at, datetime)
        assert session_data.failed_totp_attempts == 2

    def test_from_dict_missing_failed_attempts(self, sample_user_id):
        """Test from_dict defaults failed_totp_attempts to 0 if missing."""
        data_dict = {
            "user_id": str(sample_user_id),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        session_data = MFASessionData.from_dict(data_dict)
        assert session_data.failed_totp_attempts == 0

    def test_is_expired_true(self, sample_session_data):
        """Test session is expired when TTL exceeded."""
        # Set created_at to 10 minutes ago
        sample_session_data.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)

        # TTL is 5 minutes (300 seconds)
        assert sample_session_data.is_expired(ttl_seconds=300) is True

    def test_is_expired_false(self, sample_session_data):
        """Test session is not expired within TTL."""
        # Set created_at to 2 minutes ago
        sample_session_data.created_at = datetime.now(timezone.utc) - timedelta(minutes=2)

        # TTL is 5 minutes (300 seconds)
        assert sample_session_data.is_expired(ttl_seconds=300) is False

    def test_get_age_seconds(self, sample_session_data):
        """Test calculating session age in seconds."""
        # Set created_at to 100 seconds ago
        sample_session_data.created_at = datetime.now(timezone.utc) - timedelta(seconds=100)

        age = sample_session_data.get_age_seconds()
        assert 99 <= age <= 101  # Allow 1 second tolerance

    def test_increment_failed_attempts(self, sample_session_data):
        """Test incrementing failed attempts counter."""
        assert sample_session_data.failed_totp_attempts == 0

        new_count = sample_session_data.increment_failed_attempts()
        assert new_count == 1
        assert sample_session_data.failed_totp_attempts == 1

        new_count = sample_session_data.increment_failed_attempts()
        assert new_count == 2

    def test_has_exceeded_max_attempts_false(self, sample_session_data):
        """Test has_exceeded_max_attempts returns False when under limit."""
        sample_session_data.failed_totp_attempts = 3
        assert sample_session_data.has_exceeded_max_attempts(max_attempts=5) is False

    def test_has_exceeded_max_attempts_true(self, sample_session_data):
        """Test has_exceeded_max_attempts returns True when limit reached."""
        sample_session_data.failed_totp_attempts = 5
        assert sample_session_data.has_exceeded_max_attempts(max_attempts=5) is True

        sample_session_data.failed_totp_attempts = 6
        assert sample_session_data.has_exceeded_max_attempts(max_attempts=5) is True


class TestMFASessionService:
    """Test MFASessionService class."""

    def test_build_redis_key(self, mfa_service):
        """Test Redis key building."""
        session_id = str(uuid.uuid4())
        key = mfa_service._build_redis_key(session_id)

        assert key == f"mfa_session:{session_id}"

    def test_validate_session_id_format_valid(self, mfa_service):
        """Test validation accepts valid UUID."""
        valid_uuid = str(uuid.uuid4())
        assert mfa_service._validate_session_id_format(valid_uuid) is True

    def test_validate_session_id_format_invalid(self, mfa_service):
        """Test validation rejects invalid formats."""
        assert mfa_service._validate_session_id_format("not-a-uuid") is False
        assert mfa_service._validate_session_id_format("") is False
        assert mfa_service._validate_session_id_format(None) is False
        assert mfa_service._validate_session_id_format(12345) is False

    async def test_create_session(self, sample_user_id):
        """Test creating a new MFA session."""
        mock_redis = AsyncMock()
        with patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            mfa_session_id = await service.create_session(sample_user_id)

            # Should return valid UUID
            assert isinstance(mfa_session_id, str)
            uuid.UUID(mfa_session_id)  # Validates format

            # Should call Redis set with correct parameters
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args

            assert call_args.kwargs["key"] == f"mfa_session:{mfa_session_id}"
            assert call_args.kwargs["ex"] == 300  # TTL

            # Validate stored data
            stored_data = json.loads(call_args.kwargs["value"])
            assert stored_data["user_id"] == str(sample_user_id)
            assert stored_data["failed_totp_attempts"] == 0

    async def test_get_session_success(self, sample_user_id, sample_session_data):
        """Test retrieving an existing session."""
        session_id = str(uuid.uuid4())
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(sample_session_data.to_dict())

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            session = await service.get_session(session_id)

            assert session is not None
            assert session.user_id == sample_user_id
            assert session.failed_totp_attempts == 0

    async def test_get_session_not_found(self):
        """Test retrieving non-existent session returns None."""
        session_id = str(uuid.uuid4())
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            session = await service.get_session(session_id)

            assert session is None

    async def test_get_session_invalid_format(self):
        """Test get_session rejects invalid session ID format."""
        mock_redis = AsyncMock()

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            session = await service.get_session("invalid-format")

            assert session is None
            mock_redis.get.assert_not_called()

    async def test_get_session_expired(self, sample_user_id):
        """Test get_session deletes expired sessions."""
        session_id = str(uuid.uuid4())
        # Create expired session data (10 minutes ago)
        expired_data = MFASessionData(
            user_id=sample_user_id,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            failed_totp_attempts=0,
        )

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(expired_data.to_dict())

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            session = await service.get_session(session_id)

            assert session is None
            # Should delete expired session
            mock_redis.delete.assert_called_once_with(f"mfa_session:{session_id}")

    async def test_get_session_corrupted_json(self):
        """Test get_session handles corrupted JSON data."""
        session_id = str(uuid.uuid4())
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "invalid-json-data"

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            session = await service.get_session(session_id)

            assert session is None
            # Should delete corrupted session
            mock_redis.delete.assert_called_once()

    async def test_delete_session(self):
        """Test deleting a session."""
        session_id = str(uuid.uuid4())
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = True

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            result = await service.delete_session(session_id)

            assert result is True
            mock_redis.delete.assert_called_once_with(f"mfa_session:{session_id}")

    async def test_increment_failed_totp_attempts(self, sample_user_id, sample_session_data):
        """Test incrementing failed TOTP attempts."""
        session_id = str(uuid.uuid4())
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(sample_session_data.to_dict())

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            new_count = await service.increment_failed_totp_attempts(session_id)

            assert new_count == 1

            # Verify Redis was updated with incremented count
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            updated_data = json.loads(call_args.kwargs["value"])
            assert updated_data["failed_totp_attempts"] == 1

    async def test_increment_failed_totp_attempts_session_not_found(self):
        """Test incrementing attempts returns None if session not found."""
        session_id = str(uuid.uuid4())
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            result = await service.increment_failed_totp_attempts(session_id)

            assert result is None

    async def test_build_global_lockout_key(self, mfa_service, sample_user_id):
        """Test building global lockout key."""
        key = mfa_service._build_global_lockout_key(sample_user_id)
        assert key == f"mfa_fail:{str(sample_user_id)}"

    async def test_increment_global_failed_attempts(self, sample_user_id):
        """Test incrementing global failed attempts counter."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            count = await service.increment_global_failed_attempts(sample_user_id)

            assert count == 1
            mock_redis.incr.assert_called_once_with(f"mfa_fail:{str(sample_user_id)}")
            # Should set TTL on first increment
            mock_redis.expire.assert_called_once_with(
                f"mfa_fail:{str(sample_user_id)}", settings.redis.mfa_global_lockout_ttl
            )

    async def test_increment_global_failed_attempts_subsequent(self, sample_user_id):
        """Test subsequent global failed attempts don't reset TTL."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 3  # Not first increment

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            count = await service.increment_global_failed_attempts(sample_user_id)

            assert count == 3
            # Should NOT set TTL for subsequent increments
            mock_redis.expire.assert_not_called()

    async def test_is_globally_locked_out_false(self, sample_user_id):
        """Test global lockout check returns False when under limit."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "5"  # Under limit of 10

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            is_locked = await service.is_globally_locked_out(sample_user_id)

            assert is_locked is False

    async def test_is_globally_locked_out_true(self, sample_user_id):
        """Test global lockout check returns True when limit reached."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "10"  # At limit

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            is_locked = await service.is_globally_locked_out(sample_user_id)

            assert is_locked is True

    async def test_is_globally_locked_out_no_counter(self, sample_user_id):
        """Test global lockout returns False when counter doesn't exist."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            is_locked = await service.is_globally_locked_out(sample_user_id)

            assert is_locked is False

    async def test_is_globally_locked_out_invalid_data(self, sample_user_id):
        """Test global lockout handles invalid counter data."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "invalid"

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            is_locked = await service.is_globally_locked_out(sample_user_id)

            assert is_locked is False

    async def test_clear_global_lockout(self, sample_user_id):
        """Test clearing global lockout counter."""
        mock_redis = AsyncMock()

        with patch("apps.authentication.services.mfa_session.logger"), patch(
            "apps.authentication.services.mfa_session.RedisCache",
            return_value=mock_redis,
        ):
            service = MFASessionService()
            await service.clear_global_lockout(sample_user_id)

            mock_redis.delete.assert_called_once_with(f"mfa_fail:{str(sample_user_id)}")
