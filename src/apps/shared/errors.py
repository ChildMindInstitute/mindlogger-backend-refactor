"""
This module is responsible for describing shared errors
that are handled on the middleware level.
"""


class BaseError(Exception):
    def __init__(self, message="Unhandled error", *args) -> None:
        super().__init__(message, *args)


class NotContentError(BaseError):
    def __init__(self, *args) -> None:
        super().__init__(message="", *args)


class PermissionsError(BaseError):
    def __init__(self, message="Not enough permissions", *args) -> None:
        super().__init__(message, *args)


class NotFoundError(BaseError):
    def __init__(self, message="Not found error", *args) -> None:
        super().__init__(message, *args)


class ValidationError(BaseError):
    def __init__(self, message="Validation error", *args) -> None:
        super().__init__(message, *args)
