"""
This module is responsible for describing shared errors
that are handled on the middleware level.
"""

from starlette import status

from apps.shared.domain.response.errors import ErrorResponseType


class BaseError(Exception):
    def __init__(
            self,
            *_,
            message: str = "",
            status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
            type_: ErrorResponseType = ErrorResponseType.UNDEFINED,
    ) -> None:
        self._message: str = message
        self._status_code: int = status_code
        self._type: ErrorResponseType = type_

        super().__init__(message)


class ValidationError(BaseError):
    def __init__(self, *_, message="Validation error") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
