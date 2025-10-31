from datetime import datetime
from typing import Generic

from infrastructure.cache.types import _InputObject
from pydantic import BaseModel


class CacheEntry(BaseModel, Generic[_InputObject]):
    """This class extends any kind of pydantic model with meta data."""

    instance: _InputObject
    created_at: datetime
