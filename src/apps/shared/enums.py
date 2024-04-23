from enum import Enum


class Language(str, Enum):
    ENGLISH = "en"
    FRENCH = "fr"
    RUSSIAN = "ru"
    UZBEK = "uz"


class ColumnCommentType(str, Enum):
    ENCRYPTED = "encrypted"
