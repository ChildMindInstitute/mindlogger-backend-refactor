from apps.shared.errors import NotFoundError, PermissionsError, ValidationError


class TokenNotFoundError(NotFoundError):
    def __init__(self, *args) -> None:
        super().__init__("Token not found", *args)


class AuthenticationError(PermissionsError):
    def __init__(self, message="", *args) -> None:
        fallback = "Authentication service error"
        super().__init__(message or fallback, *args)


class BadCredentials(ValidationError):
    def __init__(self, message="", error="", *args) -> None:
        fallback = "Bad credentials"
        super().__init__(message or fallback, error, *args)
