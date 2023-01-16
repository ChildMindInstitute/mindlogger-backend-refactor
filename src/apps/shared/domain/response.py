from collections.abc import Mapping
from typing import Any, Generic

from pydantic import conlist
from pydantic.generics import GenericModel
from starlette import status

from apps.shared.domain.base import PublicModel
from apps.shared.domain.types import _BaseModel


class ResponseMulti(PublicModel, GenericModel, Generic[_BaseModel]):
    """Generic response model that consist multiple results."""

    results: list[_BaseModel]


class Response(PublicModel, GenericModel, Generic[_BaseModel]):
    """Generic response model that consist only one result."""

    result: _BaseModel


class ErrorResponse(PublicModel):
    """Error response model."""

    messages: conlist(str, min_items=1)  # type: ignore[valid-type]


# NOTE: This constant represents the default error response for each request
__DEFAULT_ERROR_RESPONSE: dict[str, Any] = {"model": ErrorResponse}

ResopnseType = Mapping[int | str, dict[str, Any]]

NO_CONTENT_ERROR_RESPONSES: ResopnseType = {
    status.HTTP_404_NOT_FOUND: {},
}
AUTHENTICATION_ERROR_RESPONSES: ResopnseType = {
    status.HTTP_401_UNAUTHORIZED: __DEFAULT_ERROR_RESPONSE,
    status.HTTP_403_FORBIDDEN: __DEFAULT_ERROR_RESPONSE,
}
DEFAULT_OPENAPI_RESPONSE: ResopnseType = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: __DEFAULT_ERROR_RESPONSE,
    status.HTTP_400_BAD_REQUEST: __DEFAULT_ERROR_RESPONSE,
    status.HTTP_422_UNPROCESSABLE_ENTITY: {},
}
