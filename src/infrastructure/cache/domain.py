from datetime import datetime
from typing import Generic

from pydantic.generics import GenericModel

from infrastructure.cache.types import _InputObject


class CacheEntry(GenericModel, Generic[_InputObject]):
    """This class extends any kind of pydantic model with meta data."""

    instance: _InputObject
    created_at: datetime
