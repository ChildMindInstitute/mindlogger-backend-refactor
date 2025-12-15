from typing import Generic

from pydantic import BaseModel

from apps.shared.domain.base import PublicModel
from apps.shared.domain.types import _BaseModel


class ResponseMulti(PublicModel, BaseModel, Generic[_BaseModel]):
    """Generic response model that consists of multiple results."""

    result: list[_BaseModel]
    count: int = 0


class ResponseMultiOrdering(ResponseMulti, BaseModel, Generic[_BaseModel]):
    """Generic response model that consists of multiple results and a list of sortable fields."""

    ordering_fields: list[str]


class Response(PublicModel, BaseModel, Generic[_BaseModel]):
    """Generic response model that consists of only one result."""

    result: _BaseModel | None = None
