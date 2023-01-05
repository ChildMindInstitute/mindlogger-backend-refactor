from apps.shared.errors import BaseError, NotFoundError, ValidationError


class ThemesError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Themes service error"
        super().__init__(message or fallback, *args)


class ThemeAlreadyExist(ValidationError):
    def __init__(self, *args) -> None:
        message = "Theme already exist"
        super().__init__(message, *args)


class ThemeNotFoundError(NotFoundError):
    def __init__(self, message="", *args) -> None:
        fallback = "Theme service error"
        super().__init__(message or fallback, *args)


class ThemePermissionsError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Not enough permissions"
        super().__init__(message or fallback, *args)
