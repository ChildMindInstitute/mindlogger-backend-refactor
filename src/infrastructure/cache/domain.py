from datetime import datetime
from typing import Generic, NamedTuple

from aioredis.connection import EncodableT
from pydantic.generics import GenericModel

from infrastructure.cache.types import _InputObject


class RawEntry(NamedTuple):
    """Interanl value that uses for cache conversion.
    Should not be used for something else.
    """

    key: str
    value: EncodableT


class CacheEntry(GenericModel, Generic[_InputObject]):
    """This class extends any kind of pydantic model with meta data."""

    instance: _InputObject
    created_at: datetime
