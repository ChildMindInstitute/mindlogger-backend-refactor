from apps.shared.domain.base import BaseError


class AuthenticationError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Authentication service error"
        super().__init__(message or fallback, *args)


class BadCredentials(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Bad credentials"
        super().__init__(message or fallback, *args)
