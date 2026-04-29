import unicodedata

import regex

from apps.users.errors import (
    PasswordContainsInvalidCharactersError,
    PasswordHasEmojisError,
    PasswordHasSpacesError,
    PasswordInsufficientTypesError,
    PasswordTooShortError,
)
from config import settings

# Regex for emoji (standard emjoi + regional indicators) which are not exposed as a Unicode catgory
EMOJI_REGEX = regex.compile(r"\p{Extended_Pictographic}|[\U0001F1E6-\U0001F1FF]")

# Regex for grapheme cluster for counting user-perceived characters
GRAPHEME_REGEX = regex.compile(r"\X")


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
        has_control = any(cat.startswith("C") for cat in unicodecategories)
        if has_control:
            raise PasswordContainsInvalidCharactersError()

        # Reject any whitespace or blank characters that Unicode classifies as visible
        has_whitespace = any(ch.isspace() or ch in "\u2800\u3164\u115f\u1160\uffa0" for ch in normalized)
        if has_whitespace:
            raise PasswordHasSpacesError()

        # Reject any emoji or regional indicators
        has_emoji = EMOJI_REGEX.search(normalized) is not None
        if has_emoji:
            raise PasswordHasEmojisError()

        # Minimum length as counted by graphemes
        length = len(GRAPHEME_REGEX.findall(normalized))
        if length < config.min_length:
            raise PasswordTooShortError(chars=config.min_length)

        # At least N of the following character types
        has_caseless = "Lo" in unicodecategories or "Lm" in unicodecategories  # CJK, Arabic, Hebrew, etc.
        has_lowercase = "Ll" in unicodecategories
        has_uppercase = "Lu" in unicodecategories
        has_digit = "Nd" in unicodecategories
        has_symbol = any(not cat.startswith("L") and cat != "Nd" for cat in unicodecategories)
        types_present = sum(
            (
                has_lowercase or has_caseless,  # lowercase or caseless (CJK, Arabic, Hebrew, etc.)
                has_uppercase or has_caseless,  # uppercase or caseless (CJK, Arabic, Hebrew, etc.)
                has_digit,  # digit
                has_symbol,  # symbol
            )
        )
        if types_present < config.min_character_types:
            raise PasswordInsufficientTypesError(types=config.min_character_types)

        # Phase 2: zxcvbn score check
        # Phase 2: HIBP breach check

        return normalized
