import uuid
from datetime import datetime, timedelta, timezone

import pytest

from apps.users.domain import User
from apps.users.errors import MFASetupExpiredError, MFASetupNotFoundError
from apps.users.services.totp import TOTPService, totp_service


@pytest.fixture(scope="module")
def totp_svc():
    """Create a fresh TOTP service instance for testing."""
    return TOTPService()


@pytest.fixture
def test_user():
    """Create a test user with MFA fields."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_super_admin=False,
        mfa_enabled=False,
        mfa_secret=None,
        pending_mfa_secret=None,
        pending_mfa_created_at=None,
        hashed_password="hashed",
        email_encrypted="test@example.com",
        last_seen_at=None,
    )


class TestTOTPService:
    """Unit tests for TOTP service methods."""

    def test_generate_secret(self, totp_svc: TOTPService):
        """Test secret generation returns valid base32 string."""
        secret = totp_svc.generate_secret()

        assert isinstance(secret, str)
        assert len(secret) == 32
        # Base32 should only contain A-Z and 2-7
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)

    def test_encrypt_decrypt_secret(self, totp_svc: TOTPService):
        """Test encryption and decryption round-trip."""
        original_secret = "JBSWY3DPEHPK3PXP"

        # Encrypt
        encrypted = totp_svc.encrypt_secret(original_secret)
        assert isinstance(encrypted, str)
        assert encrypted != original_secret
        assert len(encrypted) > len(original_secret)

        # Decrypt
        decrypted = totp_svc.decrypt_secret(encrypted)
        assert decrypted == original_secret

    def test_decrypt_invalid_secret_raises_error(self, totp_svc: TOTPService):
        """Test decrypting invalid data raises error."""
        with pytest.raises(Exception):
            totp_svc.decrypt_secret("invalid_encrypted_data")

    def test_generate_provisioning_uri(self, totp_svc: TOTPService):
        """Test provisioning URI generation for QR codes."""
        secret = "JBSWY3DPEHPK3PXP"
        email = "user@example.com"

        uri = totp_svc.generate_provisioning_uri(secret, email)

        assert uri.startswith("otpauth://totp/")
        # Email is URL-encoded in the URI
        assert "user%40example.com" in uri or email in uri
        assert f"secret={secret}" in uri
        assert f"issuer={totp_svc.issuer_name}" in uri

    def test_verify_code_valid(self, totp_svc: TOTPService):
        """Test verification of a valid TOTP code."""
        secret = "JBSWY3DPEHPK3PXP"

        # Generate current valid code
        current_code = totp_svc.get_current_code(secret)

        # Verify it
        assert totp_svc.verify_code(secret, current_code) is True

    def test_verify_code_invalid(self, totp_svc: TOTPService):
        """Test rejection of an invalid TOTP code."""
        secret = "JBSWY3DPEHPK3PXP"
        invalid_code = "000000"

        assert totp_svc.verify_code(secret, invalid_code) is False

    def test_verify_code_with_custom_window(self, totp_svc: TOTPService):
        """Test verification with custom valid_window override."""
        secret = "JBSWY3DPEHPK3PXP"
        current_code = totp_svc.get_current_code(secret)

        # Should work with window=0 for current code
        assert totp_svc.verify_code(secret, current_code, valid_window=0) is True

        # Invalid code should fail regardless of window
        assert totp_svc.verify_code(secret, "000000", valid_window=5) is False

    def test_get_current_code(self, totp_svc: TOTPService):
        """Test getting current TOTP code."""
        secret = "JBSWY3DPEHPK3PXP"

        code = totp_svc.get_current_code(secret)

        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()

    def test_is_pending_setup_expired_none(self, totp_svc: TOTPService):
        """Test that None created_at is considered expired."""
        assert totp_svc.is_pending_setup_expired(None) is True  # type: ignore[arg-type]

    def test_is_pending_setup_expired_old(self, totp_svc: TOTPService):
        """Test that old timestamps are expired."""
        # 20 minutes ago (way past default 10 min expiration)
        old_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
        assert totp_svc.is_pending_setup_expired(old_time) is True

    def test_is_pending_setup_expired_recent(self, totp_svc: TOTPService):
        """Test that recent timestamps are not expired."""
        # 1 minute ago (well within 10 min expiration)
        recent_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        assert totp_svc.is_pending_setup_expired(recent_time) is False

    def test_is_pending_setup_expired_boundary(self, totp_svc: TOTPService, monkeypatch):
        """Test expiration at exact boundary."""
        # Mock settings to control expiration time
        from config import settings

        monkeypatch.setattr(settings.mfa, "pending_mfa_expiration_seconds", 600)

        # Just before boundary (599 seconds) - should NOT be expired
        created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=599)
        assert totp_svc.is_pending_setup_expired(created_at) is False

        # Just after boundary (601 seconds) - should be expired
        created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=601)
        assert totp_svc.is_pending_setup_expired(created_at) is True

    def test_validate_pending_setup_success(self, totp_svc: TOTPService, test_user: User):
        """Test successful validation of pending setup."""
        # Setup test user with valid pending MFA
        secret = "JBSWY3DPEHPK3PXP"
        encrypted_secret = totp_svc.encrypt_secret(secret)
        test_user.pending_mfa_secret = encrypted_secret
        test_user.pending_mfa_created_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Should successfully validate and return decrypted secret
        decrypted = totp_svc.validate_pending_setup(test_user)
        assert decrypted == secret

    def test_validate_pending_setup_no_secret(self, totp_svc: TOTPService, test_user: User):
        """Test validation fails when no pending secret exists."""
        test_user.pending_mfa_secret = None

        with pytest.raises(MFASetupNotFoundError):
            totp_svc.validate_pending_setup(test_user)

    def test_validate_pending_setup_no_created_at(self, totp_svc: TOTPService, test_user: User):
        """Test validation fails when created_at is missing."""
        test_user.pending_mfa_secret = "some_encrypted_secret"
        test_user.pending_mfa_created_at = None

        with pytest.raises(ValueError, match="Invalid pending MFA setup state"):
            totp_svc.validate_pending_setup(test_user)

    def test_validate_pending_setup_expired(self, totp_svc: TOTPService, test_user: User):
        """Test validation fails when setup is expired."""
        secret = "JBSWY3DPEHPK3PXP"
        encrypted_secret = totp_svc.encrypt_secret(secret)
        test_user.pending_mfa_secret = encrypted_secret
        # 20 minutes ago - expired
        test_user.pending_mfa_created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)

        with pytest.raises(MFASetupExpiredError):
            totp_svc.validate_pending_setup(test_user)

    def test_validate_pending_setup_corrupted(self, totp_svc: TOTPService, test_user: User):
        """Test validation fails with corrupted encrypted secret."""
        test_user.pending_mfa_secret = "corrupted_invalid_encrypted_data"
        test_user.pending_mfa_created_at = datetime.now(timezone.utc).replace(tzinfo=None)

        with pytest.raises(ValueError, match="Failed to decrypt MFA secret"):
            totp_svc.validate_pending_setup(test_user)

    def test_totp_service_singleton(self):
        """Test that totp_service is a singleton instance."""
        assert isinstance(totp_service, TOTPService)
        assert totp_service.issuer_name is not None
        assert totp_service.valid_window >= 0
