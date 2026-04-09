import unicodedata

from apps.users.errors import (
    PasswordContainsInvalidCharactersError,
    PasswordHasSpacesError,
    PasswordInsufficientTypesError,
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

        # Memoize Unicode categories
        unicodecategories = {unicodedata.category(ch) for ch in normalized}

        # Reject control characters
        if any(cat.startswith("C") for cat in unicodecategories):
            raise PasswordContainsInvalidCharactersError()

        # Reject any whitespace
        if any(ch.isspace() for ch in normalized):
            raise PasswordHasSpacesError()

        # Minimum length
        if len(normalized) < config.min_length:
            raise PasswordTooShortError(chars=config.min_length)

        # At least N of the following character types
        types_present = sum(
            (
                any(cat == "Ll" for cat in unicodecategories),  # lowercase
                any(cat == "Lu" for cat in unicodecategories),  # uppercase
                any(cat == "Lo" or cat == "Lm" for cat in unicodecategories),  # caseless (Arabic, CJK, etc.)
                any(cat == "Nd" for cat in unicodecategories),  # digit
                any(not cat.startswith("L") and cat != "Nd" for cat in unicodecategories),  # symbol
            )
        )
        if types_present < config.min_character_types:
            raise PasswordInsufficientTypesError(types=config.min_character_types)

        # Phase 2: zxcvbn score check
        # Phase 2: HIBP breach check

        return normalized
