import unicodedata

from apps.users.errors import (
    PasswordContainsInvalidCharactersError,
    PasswordHasSpacesError,
    PasswordInsufficientTypesError,
    PasswordTooLongError,
    PasswordTooShortError,
)
from config import settings


class PasswordValidator:
    """Single source of truth for all password validation logic."""

    @staticmethod
    def normalize(password: str) -> str:
        """NFKC-normalize a password."""
        return unicodedata.normalize("NFKC", password)

    @classmethod
    def validate(cls, password: str) -> str:
        """Normalize and validate a password. Returns normalized password."""
        config = settings.password

        # Normalize password
        normalized = cls.normalize(password)

        # Reject control characters
        if any(unicodedata.category(ch).startswith("C") for ch in normalized):
            raise PasswordContainsInvalidCharactersError()

        # Reject any whitespace
        if any(ch.isspace() for ch in normalized):
            raise PasswordHasSpacesError()

        # Minimum length
        if len(normalized) < config.min_length:
            raise PasswordTooShortError()

        # Maximum length
        if len(normalized) > config.max_length:
            raise PasswordTooLongError()

        # At least N of 4 character types
        types_present = sum(
            [
                any(ch.isupper() for ch in normalized),
                any(ch.islower() for ch in normalized),
                any(ch.isdigit() for ch in normalized),
                any(not ch.isalnum() and not ch.isspace() for ch in normalized),
            ]
        )
        if types_present < config.min_character_types:
            raise PasswordInsufficientTypesError()

        # Phase 2: zxcvbn score check
        # Phase 2: HIBP breach check

        return normalized
