from typing import Generic

from pydantic.generics import GenericModel

from apps.shared.domain.base import PublicModel
from apps.shared.domain.types import _BaseModel


class ResponseMulti(PublicModel, GenericModel, Generic[_BaseModel]):
    """Generic response model that consists of multiple results."""

    result: list[_BaseModel]
    count: int = 0


class ResponseMultiOrdering(ResponseMulti, GenericModel, Generic[_BaseModel]):
    """Generic response model that consists of multiple results and a list of sortable fields."""

    ordering_fields: list[str]


class Response(PublicModel, GenericModel, Generic[_BaseModel]):
    """Generic response model that consists of only one result."""

    result: _BaseModel | None
