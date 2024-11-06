import datetime
from gettext import gettext as _

from dateutil import tz
from fastapi import Depends, HTTPException, Request
from starlette import status

from infrastructure.http.domain import MindloggerContentSource


async def get_mindlogger_content_source(
    request: Request,
) -> MindloggerContentSource:
    """Fetch the Mindlogger-Content-Source HTTP header."""

    try:
        return getattr(
            MindloggerContentSource,
            request.headers.get("mindlogger-content-source", MindloggerContentSource.web.name),
        )
    except AttributeError:
        return MindloggerContentSource.web


def get_language(request: Request) -> str:
    return request.headers.get("Content-Language", "en-US").split("-")[0]


def get_local_tz(required: bool = False):
    def _get_local_tz(request: Request) -> str | None:
        tz_str = request.headers.get("X-Timezone", None) or None
        if tz_str and not tz.gettz(tz_str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_("Wrong X-Timezone header value"))
        if not tz_str and required:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_("X-Timezone header value required"))

        return tz_str

    return _get_local_tz


def get_tz_utc_offset(required: bool = False):
    def _get_tz_utc_offset(local_tz: str | None = Depends(get_local_tz(required))) -> int | None:
        if local_tz:
            if l_tz := tz.gettz(local_tz):
                return int(datetime.datetime.now(l_tz).utcoffset().total_seconds())  # type: ignore[union-attr]
        return None

    return _get_tz_utc_offset
