import datetime

import pytest
import pytz
from fastapi import HTTPException, Request

from infrastructure.http import get_local_tz, get_tz_utc_offset


@pytest.mark.parametrize(
    "headers,expected",
    (
        ([(b"x-timezone", b"US/Pacific")], "US/Pacific"),
        ([(b"x-timezone", b"")], None),
        ([], None),
    ),
)
def test_get_local_tz(headers: list, expected: str | None):
    request = Request(
        {
            "type": "http",
            "headers": headers,
        }
    )
    assert get_local_tz()(request) == expected


@pytest.mark.parametrize(
    "headers,required,details",
    (
        ([(b"x-timezone", b"")], True, "X-Timezone header value required"),
        ([], True, "X-Timezone header value required"),
        ([(b"x-timezone", b"wrong-timezone")], False, "Wrong X-Timezone header value"),
    ),
)
def test_get_local_tz__exception(headers: list, required: bool, details: str):
    request = Request(
        {
            "type": "http",
            "headers": headers,
        }
    )
    with pytest.raises(HTTPException) as e:
        get_local_tz(required=required)(request)
    assert e.value.detail == details


@pytest.mark.parametrize(
    "timezone,offset",
    (
        ("UTC", 0),
        ("EST", -5 * 60 * 60),
        ("US/Pacific", -8 * 60 * 60),
        ("wrong-timezone", None),
        (None, None),
    ),
)
def test_get_tz_utc_offset(timezone: str | None, offset: int):
    offset_without_dst = offset
    if timezone is not None and offset is not None:
        tz = pytz.timezone(timezone)
        now = datetime.datetime.now().astimezone(tz)
        now_dst_delta = now.dst()
        offset_without_dst = offset + int(now_dst_delta.total_seconds() if now_dst_delta else 0)
    assert get_tz_utc_offset()(timezone) == offset_without_dst
