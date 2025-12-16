"""TOTP service for MFA — secret generation, encryption, provisioning URI, and verification."""

import time
from datetime import datetime, timezone

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from apps.users.domain import User
from apps.users.errors import MFASetupExpiredError, MFASetupNotFoundError
from config import settings


class TOTPService:
    """TOTP operations."""

    def __init__(self):
        """Load config and prepare Fernet."""
        self.encryption_key = settings.mfa.encryption_key_bytes
        self.fernet = Fernet(self.encryption_key)
        self.issuer_name = settings.mfa.totp_issuer_name
        self.valid_window = settings.mfa.totp_valid_window

    def generate_secret(self) -> str:
        """Return a new base32 TOTP secret."""
        return pyotp.random_base32()

    def encrypt_secret(self, secret: str) -> str:
        """Encrypt and return secret string."""
        encrypted_bytes = self.fernet.encrypt(secret.encode())
        return encrypted_bytes.decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt and return secret string."""
        decrypted_bytes = self.fernet.decrypt(encrypted_secret.encode())
        return decrypted_bytes.decode()

    def generate_provisioning_uri(self, secret: str, user_email: str) -> str:
        """Return provisioning URI for QR code."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=user_email, issuer_name=self.issuer_name)

    def verify_code(self, secret: str, code: str, valid_window: int | None = None) -> bool:
        """Verify a 6-digit TOTP code. Optionally override valid_window."""
        totp = pyotp.TOTP(secret)
        window = self.valid_window if valid_window is None else valid_window
        return totp.verify(code, valid_window=window)

    def get_current_code(self, secret: str) -> str:
        """Return current TOTP code (for tests)."""
        totp = pyotp.TOTP(secret)
        return totp.now()

    def get_current_time_step(self) -> int:
        """
        Get current TOTP time step (epoch / 30 seconds).

        Returns:
            Current time step as integer
        """
        return int(time.time() // 30)

    def verify_with_replay_check(self, secret: str, code: str, last_used_step: int | None) -> tuple[bool, int | None]:
        """
        Verify TOTP code with replay protection.

        Args:
            secret: Decrypted TOTP secret
            code: User-provided 6-digit code
            last_used_step: Last successfully used time step (None if never used)

        Returns:
            Tuple of (is_valid, time_step_used)
            - is_valid: True if code is valid and not replayed
            - time_step_used: The time step of the valid code, or None if invalid
        """
        totp = pyotp.TOTP(secret)
        current_step = self.get_current_time_step()

        # Check valid_window range (current, -1, +1)
        for offset in [0, -1, 1]:
            check_step = current_step + offset

            # Skip if this step was already used (replay protection)
            if last_used_step is not None and check_step <= last_used_step:
                continue

            # Generate code for this time step
            expected_code = totp.at(check_step * 30)

            if expected_code == code:
                return True, check_step

        return False, None

    def is_pending_setup_expired(self, created_at: datetime) -> bool:
        """Return True if pending setup is older than configured expiration."""
        if not created_at:
            return True

        # Get current time without timezone (to match created_at which is naive)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Calculate elapsed time in seconds
        elapsed_seconds = (now - created_at).total_seconds()

        # Check against configured expiration time
        return elapsed_seconds > settings.mfa.pending_mfa_expiration_seconds

    def validate_pending_setup(self, user: User) -> str:
        """Validate pending MFA setup and return decrypted secret."""
        # Check if user has pending MFA setup
        if not user.pending_mfa_secret:
            raise MFASetupNotFoundError()

        if not user.pending_mfa_created_at:
            raise ValueError("Invalid pending MFA setup state.")

        # Check if setup has expired
        if self.is_pending_setup_expired(user.pending_mfa_created_at):
            raise MFASetupExpiredError()

        # Decrypt and return the secret
        try:
            decrypted_secret = self.decrypt_secret(user.pending_mfa_secret)
            return decrypted_secret
        except InvalidToken:
            raise ValueError("Failed to decrypt MFA secret. Setup may be corrupted.")


# Create a singleton instance
totp_service = TOTPService()
