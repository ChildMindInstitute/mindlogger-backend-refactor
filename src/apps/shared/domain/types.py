import datetime
from collections.abc import Mapping
from typing import Annotated, Any, TypeVar

from pydantic import BaseModel, BeforeValidator, PlainSerializer

from .base import parse_obj_as

__all__ = [
    "_BaseModel",
    "ResponseType",
    "TimeHHMM",
    "TimeHoursMinutes",
    "TruncatedDate",
    "TruncatedInt",
]

_BaseModel = TypeVar("_BaseModel", bound=(BaseModel | dict | str | int | None))

ResponseType = Mapping[int | str, dict[str, Any]]


#################
# datetime.time #
#################


def ensure_time(v: Any) -> datetime.time:
    """Convert dict or string to datetime.time.

    - {"hours": int, "minutes": int} dict format
    - "HH:MM" string format
    - datetime.time passthrough
    """
    if isinstance(v, dict):
        return dict_to_time(v)
    elif isinstance(v, str):
        return string_to_time(v)
    elif isinstance(v, datetime.time):
        return v
    raise ValueError(f"Cannot convert {type(v).__name__} to time")


def dict_to_time(time_dict: dict[str, int]) -> datetime.time:
    """Convert {"hours": int, "minutes": int} dict to datetime.time."""
    if "hours" in time_dict and "minutes" in time_dict:
        return datetime.time(hour=int(time_dict["hours"]), minute=int(time_dict["minutes"]))
    raise ValueError("Invalid time dictionary structure. Expected 'hours' and 'minutes' keys.")


def string_to_time(time_string: str) -> datetime.time:
    """Convert "HH:MM" string to datetime.time."""
    try:
        return datetime.datetime.strptime(time_string, "%H:%M").time()
    except ValueError:
        raise ValueError("Invalid time string format. Expected 'HH:MM'.")


def time_to_dict(v: datetime.time) -> dict[str, int]:
    """Serialize datetime.time as {"hours": int, "minutes": int} dict."""
    return {"hours": v.hour, "minutes": v.minute}


def time_to_string(v: datetime.time) -> str:
    """Serialize datetime.time as "HH:MM" string."""
    return v.strftime("%H:%M")


TimeHHMM = Annotated[
    datetime.time,
    BeforeValidator(ensure_time),
    PlainSerializer(time_to_string),
]


TimeHoursMinutes = Annotated[
    datetime.time,
    BeforeValidator(ensure_time),
    PlainSerializer(time_to_dict),
]


#################
# datetime.date #
#################


def truncate_time(v: Any) -> datetime.date:
    """Truncate time and return date only.

    Mimics Pydantic 1 behavior which automatically truncated non-zero
    time when validating dates.
    """
    return parse_obj_as(datetime.datetime, v).date()


TruncatedDate = Annotated[datetime.date, BeforeValidator(truncate_time)]


#######
# int #
#######


def truncate_decimal(v: Any) -> int:
    """Truncate decimal and return an integer.

    This restores Pydantic 1 behavior which automatically truncates
    decimal when validating non-integers for integer fields.
    """
    return int(parse_obj_as(float, v))


TruncatedInt = Annotated[int, BeforeValidator(truncate_decimal)]
