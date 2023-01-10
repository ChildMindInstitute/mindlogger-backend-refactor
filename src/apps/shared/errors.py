"""
This module is responsible for describing shared errors
that are handled on the middleware level.
"""


class BaseError(Exception):
    def __init__(self, message="", *args) -> None:
        fallback = "Unhandled error"
        super().__init__(message or fallback, *args)


class NotContentError(BaseError):
    def __init__(self, *args) -> None:
        super().__init__("", *args)


class PermissionsError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Not enough permissions"
        super().__init__(message or fallback, *args)


class NotFoundError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Not found error"
        super().__init__(message or fallback, *args)


class ValidationError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Validation error"
        super().__init__(message or fallback, *args)
