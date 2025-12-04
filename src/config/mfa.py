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

    @property
    def encryption_key_bytes(self) -> bytes:
        """Get the encryption key as bytes."""
        if not self.totp_encryption_key:
            raise ValueError("MFA__TOTP_ENCRYPTION_KEY environment variable is not set")
        return self.totp_encryption_key.encode()

    class Config:
        env_prefix = "MFA__"
