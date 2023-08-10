import mimetypes
import uuid
from gettext import gettext as _
from urllib.parse import urlparse

import requests
from pydantic.color import Color

__all__ = [
    "validate_image",
    "validate_color",
    "validate_audio",
    "extract_history_version",
    "validate_uuid",
]

from apps.shared.exception import ValidationError


class InvalidImageError(ValidationError):
    message = _("Invalid image.")


class InvalidColorError(ValidationError):
    message = _("Invalid color.")


class InvalidAudioError(ValidationError):
    message = _("Invalid audio file.")


class InvalidUUIDError(ValidationError):
    zero_path = None
    message = _("Invalid uuid value.")


def validate_image(value: str) -> str:
    if value.startswith("http"):
        type = (
            _get_mimetype_from_url_without_download(value)
            or _get_mimetype_from_url(value)
            or ""
        )
        if type.startswith("image/"):
            return value

    if (mimetypes.guess_type(value)[0] or "").startswith("image/"):
        return value
    raise InvalidImageError()


def _get_mimetype_from_url_without_download(value: str) -> str | None:
    try:
        res = urlparse(value)
        path = res.path
        return mimetypes.guess_type(path)[0] or None
    except Exception:
        return None


def _get_mimetype_from_url(value: str) -> str | None:
    try:
        r = requests.head(value)
        return r.headers.get("content-type")
    except Exception:
        return None


def validate_color(value: str | Color) -> str:
    if type(value) is Color:
        return value.as_hex()
    raise InvalidColorError()


def validate_audio(value: str) -> str:
    # validate file format is mp3 or wav
    type_ = mimetypes.guess_type(value)[0] or ""
    supported = (
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/x-pn-wav",
        "audio/wave",
        "video/mpeg",
        "video/webm",
    )
    if any(type_.startswith(mime_type) for mime_type in supported):
        return value

    raise InvalidAudioError()


def extract_history_version(value, values):
    """
    Requires id_version in values. Format: <uuid4>_<version_str>
    """
    if val := values.get("id_version"):
        return val[37:]

    return value


def validate_uuid(value):
    # if none, generate a new id
    if value is None:
        return str(uuid.uuid4())
    if not isinstance(value, str) or not uuid.UUID(value):
        raise InvalidUUIDError()
    return value
