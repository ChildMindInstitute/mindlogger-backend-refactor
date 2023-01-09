from apps.shared.errors import BaseError, NotFoundError, ValidationError


class TokenNotFoundError(NotFoundError):
    def __init__(self, *args) -> None:
        super().__init__("Token not found", *args)


class AuthenticationError(BaseError):
    def __init__(self, *args) -> None:
        fallback = "Could not validate credentials"
        super().__init__(fallback, *args)


class PermissionsError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Not enough permissions"
        super().__init__(message or fallback, *args)


class BadCredentials(ValidationError):
    def __init__(self, message="", *args) -> None:
        fallback = "Bad credentials"
        super().__init__(message or fallback, *args)
