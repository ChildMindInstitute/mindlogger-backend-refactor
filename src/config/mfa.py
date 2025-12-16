from pydantic import BaseModel


class MFASettings(BaseModel):
    """Settings for Multi-Factor Authentication (MFA) using TOTP."""

    # Fernet encryption key for encrypting TOTP secrets
    # This should be a base64-encoded 32-byte key generated using Fernet.generate_key()
    totp_encryption_key: str | None = None

    # TOTP issuer name (shown in authenticator apps)
    totp_issuer_name: str = "MindLogger"

    # TOTP valid window (number of time steps to check before/after current time)
    # Default is 1, which allows codes from 30 seconds before and after
    totp_valid_window: int = 1

    # Pending MFA setup expiration time in seconds (default: 10 minutes)
    pending_mfa_expiration_seconds: int = 600

    # Recovery code encryption key (base64-encoded 32-byte Fernet key)
    recovery_code_encryption_key: str | None = None

    # Number of recovery codes to generate per user
    recovery_code_count: int = 10

    # Length of random characters in recovery code (formatted as XXXXX-XXXXX)
    recovery_code_length: int = 10

    @property
    def encryption_key_bytes(self) -> bytes:
        """Get the encryption key as bytes."""
        if not self.totp_encryption_key:
            raise ValueError("MFA__TOTP_ENCRYPTION_KEY environment variable is not set")
        return self.totp_encryption_key.encode()

    @property
    def recovery_code_key_bytes(self) -> bytes:
        """Get the recovery code encryption key as bytes."""
        if not self.recovery_code_encryption_key:
            raise ValueError("MFA__RECOVERY_CODE_ENCRYPTION_KEY environment variable is not set")
        return self.recovery_code_encryption_key.encode()
