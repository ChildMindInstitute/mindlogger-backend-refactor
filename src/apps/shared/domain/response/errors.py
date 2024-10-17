from enum import StrEnum
from typing import Any

from pydantic import Field, conlist
from starlette import status

from apps.shared.domain.base import PublicModel
from apps.shared.domain.types import ResponseType


class ErrorResponseType(StrEnum):
    UNDEFINED = "UNDEFINED"


class ErrorResponseMessage(PublicModel):
    """Error response message model."""

    en: str = Field(
        description="This field represent english representation of an error",
        min_length=1,
    )


class ErrorResponse(PublicModel):
    """Error response model."""

    message: str = Field(description="This field represent the objects " "with language-specific errors")
    type: str = Field(
        description="This field represents the business-specific error type",
        default=ErrorResponseType.UNDEFINED,
    )
    path: list = Field(
        description="The path to the field that raised the error",
        default_factory=list,
    )


class ErrorResponseMulti(PublicModel):
    """The public error respnse model that includes multiple objects."""

    result: conlist(ErrorResponse)  # type: ignore


# NOTE: This constant represents the default error response for each request
__DEFAULT_ERROR_RESPONSE: dict[str, Any] = {"model": ErrorResponseMulti}

NO_CONTENT_ERROR_RESPONSES: ResponseType = {
    status.HTTP_404_NOT_FOUND: {},
}
AUTHENTICATION_ERROR_RESPONSES: ResponseType = {
    status.HTTP_401_UNAUTHORIZED: __DEFAULT_ERROR_RESPONSE,
    status.HTTP_403_FORBIDDEN: __DEFAULT_ERROR_RESPONSE,
}
DEFAULT_OPENAPI_RESPONSE: ResponseType = {
    # status.HTTP_500_INTERNAL_SERVER_ERROR: __DEFAULT_ERROR_RESPONSE,
    status.HTTP_400_BAD_REQUEST: __DEFAULT_ERROR_RESPONSE,
    status.HTTP_422_UNPROCESSABLE_ENTITY: __DEFAULT_ERROR_RESPONSE,
}
