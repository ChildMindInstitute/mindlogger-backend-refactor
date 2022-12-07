from apps.shared.errors import BaseError, NotFoundError, ValidationError


class AppletsError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Applets service error"
        super().__init__(message or fallback, *args)


class AppletAlreadyExist(ValidationError):
    def __init__(self, *args) -> None:
        message = "Applet already exist"
        super().__init__(message, *args)


class AppletNotFoundError(NotFoundError):
    def __init__(self, message="", *args) -> None:
        fallback = "Applets service error"
        super().__init__(message or fallback, *args)


class UserAppletAccessesNotFound(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "User's appletaccess not found"
        super().__init__(message or fallback, *args)
