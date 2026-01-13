from collections.abc import Mapping
from typing import Annotated, Any, TypeVar

from pydantic import BaseModel, BeforeValidator

from .base import parse_obj_as

__all__ = [
    "_BaseModel",
    "ResponseType",
]

_BaseModel = TypeVar("_BaseModel", bound=(BaseModel | dict | str | int | None))

ResponseType = Mapping[int | str, dict[str, Any]]


def truncate_decimal(v: Any) -> int:
    """Truncate decimal and return an integer.

    This restores Pydantic 1 behavior which automatically truncates
    decimal when validating non-integers for integer fields.
    """
    return int(parse_obj_as(float, v))


TruncatedInt = Annotated[int, BeforeValidator(truncate_decimal)]
