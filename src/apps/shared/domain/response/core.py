from typing import Generic

from pydantic.generics import GenericModel

from apps.shared.domain.base import PublicModel
from apps.shared.domain.types import _BaseModel


class ResponseMulti(PublicModel, GenericModel, Generic[_BaseModel]):
    """Generic response model that consist multiple results."""

    results: list[_BaseModel]


class Response(PublicModel, GenericModel, Generic[_BaseModel]):
    """Generic response model that consist only one result."""

    result: _BaseModel
