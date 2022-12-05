from typing import Generic

from pydantic import conlist
from pydantic.generics import GenericModel

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
