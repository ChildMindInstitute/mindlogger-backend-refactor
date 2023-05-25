from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

__all__ = [
    "_BaseModel",
    "ResponseType",
]

_BaseModel = TypeVar("_BaseModel", bound=(BaseModel | dict))

ResponseType = Mapping[int | str, dict[str, Any]]
