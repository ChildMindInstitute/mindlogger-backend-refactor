import datetime
from collections.abc import Mapping
from typing import Annotated, Any, TypeVar

from pydantic import BaseModel, BeforeValidator

from .base import parse_obj_as

__all__ = [
    "_BaseModel",
    "ResponseType",
    "TruncatedDate",
    "TruncatedInt",
]

_BaseModel = TypeVar("_BaseModel", bound=(BaseModel | dict | str | int | None))

ResponseType = Mapping[int | str, dict[str, Any]]


def truncate_time(v: Any) -> datetime.date:
    """Truncate time and return date only.

    Mimics Pydantic 1 behavior which automatically truncated non-zero
    time when validating dates.
    """
    return parse_obj_as(datetime.datetime, v).date()


TruncatedDate = Annotated[datetime.date, BeforeValidator(truncate_time)]


def truncate_decimal(v: Any) -> int:
    """Truncate decimal and return an integer.

    This restores Pydantic 1 behavior which automatically truncates
    decimal when validating non-integers for integer fields.
    """
    return int(parse_obj_as(float, v))


TruncatedInt = Annotated[int, BeforeValidator(truncate_decimal)]
