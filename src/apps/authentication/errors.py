from starlette import status

from apps.shared.errors import BadRequestError, BaseError


class AuthenticationError(BaseError):
    def __init__(self, message="Could not validate credentials") -> None:
        super().__init__(
            message=message, status_code=status.HTTP_401_UNAUTHORIZED
        )


class PermissionsError(BaseError):
    def __init__(self, message="Not enough permissions") -> None:
        super().__init__(
            message=message, status_code=status.HTTP_403_FORBIDDEN
        )


class BadCredentials(BadRequestError):
    def __init__(self, message="Bad credentials") -> None:
        super().__init__(message=message)
