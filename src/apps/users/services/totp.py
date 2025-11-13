"""
TOTP (Time-based One-Time Password) service for Multi-Factor Authentication.

This service handles:
- Generating TOTP secrets
- Encrypting/decrypting secrets
- Creating provisioning URIs for QR codes
- Verifying TOTP codes
"""

from datetime import datetime, timezone

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from apps.users.domain import User
from apps.users.errors import MFASetupExpiredError, MFASetupNotFoundError
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
    
    def is_pending_setup_expired(self, created_at: datetime) -> bool:
        """
        Check if the pending MFA setup has expired.

        Args:
            created_at: The datetime when the pending setup was created

        Returns:
            bool: True if expired (> expiration_seconds), False otherwise
        """
        if not created_at:
            return True
        
        # Get current time without timezone (to match created_at which is naive)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Calculate elapsed time in seconds
        elapsed_seconds = (now - created_at).total_seconds()
        
        # Check against configured expiration time (600 seconds = 10 minutes)
        return elapsed_seconds > settings.mfa.pending_mfa_expiration_seconds
    
    def validate_pending_setup(self, user: User) -> str:
        """
        Validate that user has a valid pending MFA setup and return decrypted secret.

        Args:
            user: The user attempting to verify TOTP setup

        Returns:
            str: The decrypted TOTP secret

        Raises:
            MFASetupNotFoundError: If no pending setup exists
            MFASetupExpiredError: If pending setup has expired
            ValueError: If decryption fails (corrupted setup)
        """
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
