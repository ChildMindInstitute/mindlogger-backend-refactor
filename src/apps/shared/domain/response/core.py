from typing import Generic

from pydantic.generics import GenericModel

from apps.shared.domain.base import PublicModel
from apps.shared.domain.types import _BaseModel


class ResponseMulti(PublicModel, GenericModel, Generic[_BaseModel]):
    """Generic response model that consist multiple result."""

    result: list[_BaseModel]
    count: int = 0


class Response(PublicModel, GenericModel, Generic[_BaseModel]):
    """Generic response model that consist only one result."""

    result: _BaseModel | None
