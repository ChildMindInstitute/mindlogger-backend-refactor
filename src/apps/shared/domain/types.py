from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel

__all__ = [
    "_BaseModel",
    "ResponseType",
]

_BaseModel = TypeVar("_BaseModel", bound=(BaseModel | dict | str | int | None))

ResponseType = Mapping[int | str, dict[str, Any]]
