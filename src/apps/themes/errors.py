from apps.shared.errors import BaseError, NotFoundError, ValidationError


class ThemesError(BaseError):
    def __init__(self, message: str = "Themes service error") -> None:
        super().__init__(message=message)


class ThemeAlreadyExist(ValidationError):
    def __init__(self, message: str = "Theme already exist") -> None:
        super().__init__(message=message)


class ThemeNotFoundError(NotFoundError):
    def __init__(self, key: str, value: str) -> None:
        super().__init__(message=f"No such theme with {key}={value}.")
