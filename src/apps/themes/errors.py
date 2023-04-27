from apps.shared.enums import Language
from apps.shared.errors import BaseError, ValidationError
from apps.shared.exception import NotFoundError


class ThemeNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "No such theme with {key}={value}."
    }


class ThemesError(BaseError):
    def __init__(self, message: str = "Themes service error") -> None:
        super().__init__(message=message)


class ThemeAlreadyExist(ValidationError):
    def __init__(self, message: str = "Theme already exist") -> None:
        super().__init__(message=message)
