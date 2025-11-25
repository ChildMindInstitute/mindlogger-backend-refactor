"""Service for generating and managing MFA recovery codes."""

import datetime
import secrets
import string
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.cruds.recovery_code import RecoveryCodeCRUD
from apps.authentication.domain.recovery_code import RecoveryCodeCreate
from apps.shared.bcrypt import get_password_hash, verify
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from config import settings
from cryptography.fernet import Fernet

__all__ = [
    "generate_random_code",
    "format_recovery_code",
    "hash_recovery_code",
    "verify_recovery_code",
    "encrypt_recovery_code",
    "decrypt_recovery_code",
    "generate_recovery_codes",
]


def generate_random_code() -> str:
    """
    Generate a random recovery code.

    Returns:
        str: Random alphanumeric code in format XXXXX-XXXXX (e.g., "A3F7K-9B2Q5")
    """
    # Get length from config (10 alphanumeric characters)
    length = settings.mfa.recovery_code_length

    # Generate random alphanumeric string (uppercase letters and digits)
    # Using secrets for cryptographically strong random generation
    alphabet = string.ascii_uppercase + string.digits
    random_chars = "".join(secrets.choice(alphabet) for _ in range(length))

    # Format as XXXXX-XXXXX
    return format_recovery_code(random_chars)


def format_recovery_code(code: str) -> str:
    """
    Format recovery code with hyphen in the middle.

    Args:
        code: Unformatted alphanumeric string (e.g., "A3F7K9B2Q5")

    Returns:
        str: Formatted code with hyphen (e.g., "A3F7K-9B2Q5")
    """
    if len(code) != settings.mfa.recovery_code_length:
        raise ValueError(f"Code must be {settings.mfa.recovery_code_length} characters")

    # Split in middle and add hyphen
    mid = len(code) // 2
    return f"{code[:mid]}-{code[mid:]}"


def hash_recovery_code(code: str) -> str:
    """
    Hash a recovery code using bcrypt for secure storage.

    The code is hashed (not encrypted) so it can be verified later but never
    retrieved in plaintext from the hash.

    Args:
        code: Recovery code to hash (e.g., "A3F7K-9B2Q5")

    Returns:
        str: Bcrypt hash of the code (e.g., "$2b$12$...")
    """
    return get_password_hash(code)


def verify_recovery_code(code: str, code_hash: str) -> bool:
    """
    Verify a recovery code against its bcrypt hash.

    Args:
        code: Plain recovery code to verify (e.g., "A3F7K-9B2Q5")
        code_hash: Bcrypt hash to verify against (e.g., "$2b$12$...")

    Returns:
        bool: True if code matches hash, False otherwise
    """
    return verify(code, code_hash)


def encrypt_recovery_code(code: str) -> str:
    """
    Encrypt a recovery code using Fernet for secure storage and later display.

    Unlike hashing, encryption is reversible - we can decrypt the code later
    to show it to the user. This is stored alongside the hash for display purposes.

    Args:
        code: Plain recovery code to encrypt (e.g., "A3F7K-9B2Q5")

    Returns:
        str: Fernet-encrypted code (base64-encoded, e.g., "gAAAAB...")
    """
    # Get encryption key from config
    encryption_key = settings.mfa.recovery_code_key_bytes
    fernet = Fernet(encryption_key)

    # Encrypt and return as string
    encrypted_bytes = fernet.encrypt(code.encode())
    return encrypted_bytes.decode()


def decrypt_recovery_code(encrypted_code: str) -> str:
    """
    Decrypt a recovery code encrypted with Fernet.

    Args:
        encrypted_code: Fernet-encrypted code (e.g., "gAAAAB...")

    Returns:
        str: Decrypted recovery code (e.g., "A3F7K-9B2Q5")

    Raises:
        cryptography.fernet.InvalidToken: If encrypted_code is invalid or tampered
    """
    # Get encryption key from config
    encryption_key = settings.mfa.recovery_code_key_bytes
    fernet = Fernet(encryption_key)

    # Decrypt and return as string
    decrypted_bytes = fernet.decrypt(encrypted_code.encode())
    return decrypted_bytes.decode()


async def generate_recovery_codes(
    session: AsyncSession,
    user_id: uuid.UUID,
    count: int | None = None,
) -> list[str]:
    """
    Generate recovery codes for a user and store them in the database.

    This function orchestrates the complete recovery code generation flow:
    1. Generate random codes
    2. Hash each code for verification
    3. Encrypt each code for display
    4. Store both hash and encrypted versions in DB
    5. Update user's recovery_codes_generated_at timestamp

    Args:
        session: Database session for transactions
        user_id: UUID of the user to generate codes for
        count: Number of codes to generate (defaults to config value)

    Returns:
        list[str]: Plaintext recovery codes for one-time display to user
                   Format: ["A3F7K-9B2Q5", "B2C4D-6E8F0", ...]

    Example:
        codes = await generate_recovery_codes(session, user_id, count=10)
        # Display codes to user once, they cannot be retrieved later
    """
    # Use config default if count not specified
    if count is None:
        count = settings.mfa.recovery_code_count

    # Step 1: Generate random plaintext codes
    plaintext_codes = [generate_random_code() for _ in range(count)]

    # Step 2: Create domain models with hashed and encrypted versions
    recovery_code_creates = []
    for code in plaintext_codes:
        code_hash = hash_recovery_code(code)
        code_encrypted = encrypt_recovery_code(code)

        recovery_code_creates.append(
            RecoveryCodeCreate(
                user_id=user_id,
                code_hash=code_hash,
                code_encrypted=code_encrypted,
                used=False,
                used_at=None,
            )
        )

    # Step 3: Store all codes in database (batch insert)
    recovery_code_crud = RecoveryCodeCRUD(session)
    await recovery_code_crud.create_many(recovery_code_creates)

    # Step 4: Update user's recovery_codes_generated_at timestamp
    users_crud = UsersCRUD(session)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    await users_crud.update_by_id(
        pk=user_id,
        update_schema=UserSchema(recovery_codes_generated_at=now),
    )

    # Step 5: Return plaintext codes for one-time display
    return plaintext_codes
