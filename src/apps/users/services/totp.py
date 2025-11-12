"""
TOTP (Time-based One-Time Password) service for Multi-Factor Authentication.

This service handles:
- Generating TOTP secrets
- Encrypting/decrypting secrets
- Creating provisioning URIs for QR codes
- Verifying TOTP codes
"""

import pyotp
from cryptography.fernet import Fernet

from config import settings


class TOTPService:
    """Service for handling TOTP operations."""

    def __init__(self):
        """Initialize the TOTP service with encryption key from settings."""
        self.encryption_key = settings.mfa.encryption_key_bytes
        self.fernet = Fernet(self.encryption_key)
        self.issuer_name = settings.mfa.totp_issuer_name
        self.valid_window = settings.mfa.totp_valid_window

    def generate_secret(self) -> str:
        """
        Generate a random base32-encoded TOTP secret.

        Returns:
            str: A 32-character base32-encoded secret
        """
        return pyotp.random_base32()

    def encrypt_secret(self, secret: str) -> str:
        """
        Encrypt a TOTP secret using Fernet encryption.

        Args:
            secret: The plain text TOTP secret to encrypt

        Returns:
            str: The encrypted secret as a string
        """
        encrypted_bytes = self.fernet.encrypt(secret.encode())
        return encrypted_bytes.decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """
        Decrypt an encrypted TOTP secret.

        Args:
            encrypted_secret: The encrypted TOTP secret

        Returns:
            str: The decrypted plain text secret

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        decrypted_bytes = self.fernet.decrypt(encrypted_secret.encode())
        return decrypted_bytes.decode()

    def generate_provisioning_uri(self, secret: str, user_email: str) -> str:
        """
        Generate a provisioning URI for QR code generation.

        This URI can be converted to a QR code that users scan with their
        authenticator app (Google Authenticator, Authy, etc.).

        Args:
            secret: The TOTP secret (plain text, not encrypted)
            user_email: The user's email address (shown in authenticator app)

        Returns:
            str: A provisioning URI in the format:
                 otpauth://totp/MindLogger:user@example.com?secret=ABC123&issuer=MindLogger
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=user_email, issuer_name=self.issuer_name)

    def verify_code(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code against a secret.

        Args:
            secret: The TOTP secret (plain text, not encrypted)
            code: The 6-digit code to verify

        Returns:
            bool: True if the code is valid, False otherwise
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=self.valid_window)

    def get_current_code(self, secret: str) -> str:
        """
        Get the current TOTP code for a secret.

        Useful for testing purposes.

        Args:
            secret: The TOTP secret (plain text, not encrypted)

        Returns:
            str: The current 6-digit TOTP code
        """
        totp = pyotp.TOTP(secret)
        return totp.now()


# Create a singleton instance
totp_service = TOTPService()
