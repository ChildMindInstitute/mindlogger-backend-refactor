from datetime import datetime
from typing import Generic

from pydantic import BaseModel

from infrastructure.cache.types import _InputObject


class CacheEntry(BaseModel, Generic[_InputObject]):
    """This class extends any kind of pydantic model with meta data."""

    instance: _InputObject
    created_at: datetime
