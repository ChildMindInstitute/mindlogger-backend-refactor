from typing import TypeVar

from pydantic import BaseModel

__all__ = ["_BaseModel"]

_BaseModel = TypeVar("_BaseModel", bound=BaseModel)
