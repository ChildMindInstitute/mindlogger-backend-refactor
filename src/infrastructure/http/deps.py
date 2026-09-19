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


async def get_optional_mindlogger_content_source(
    request: Request,
) -> MindloggerContentSource | None:
    """Fetch the Mindlogger-Content-Source HTTP header without assuming a default.

    Unlike ``get_mindlogger_content_source``, a missing or unrecognized header
    resolves to ``None`` ("unknown client") rather than ``web``. Authentication
    decisions (e.g. per-client token lifetimes) must not guess: mobile app
    versions released before might not send the header and would
    otherwise be misclassified as web clients.
    """

    header_value = request.headers.get("mindlogger-content-source")
    if header_value is None:
        return None
    try:
        return MindloggerContentSource(header_value)
    except ValueError:
        return None


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
