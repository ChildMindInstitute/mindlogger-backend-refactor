import datetime
import mimetypes
import uuid
from copy import deepcopy
from gettext import gettext as _
from urllib.parse import urlparse

import nh3
import requests
from pydantic.color import Color

__all__ = [
    "validate_image",
    "validate_color",
    "validate_audio",
    "extract_history_version",
    "validate_uuid",
    "lowercase",
    "lowercase_email",
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
        type = _get_mimetype_from_url_without_download(value) or _get_mimetype_from_url(value) or ""
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


def datetime_from_ms(value):
    if isinstance(value, int):
        if (
            value > datetime.datetime(year=2000, month=1, day=1, tzinfo=datetime.timezone.utc).timestamp() * 1000
        ):  # ms, assume date > 2000-01-01
            value = value / 1000  # wtf, rework this
        return datetime.datetime.utcfromtimestamp(value)
    return value


def lowercase_email(values):
    email = values.get("email")
    if email:
        values["email"] = email.lower()
    return values


def translate(val):
    lang = "en"
    if isinstance(val, dict):
        return val.get(lang, None)


def lowercase(value: str | None):
    if value is not None:
        value = value.lower()
    return value


def array_from_string(comma_separated: bool = False):
    def _array_from_string(val):
        if comma_separated and isinstance(val, list) and len(val) == 1:
            val = val[0]
        if isinstance(val, str):
            if not val:
                return []
            val = val.split(",")
        return val

    return _array_from_string


nh3_attributes = deepcopy(nh3.ALLOWED_ATTRIBUTES)
nh3_rollback = {"&amp;": "&"}
default_attributes = {
    "id",
    "data-line",
    "class",
}
nh3_attributes["h1"] = default_attributes
nh3_attributes["h2"] = default_attributes
nh3_attributes["h3"] = default_attributes
nh3_attributes["h4"] = default_attributes
nh3_attributes["h5"] = default_attributes
nh3_attributes["h6"] = default_attributes
nh3_attributes["div"] = default_attributes
nh3_attributes["p"] = default_attributes
nh3_attributes["ul"] = default_attributes
nh3_attributes["ol"] = default_attributes
nh3_attributes["li"] = default_attributes
nh3_attributes["details"] = default_attributes
nh3_attributes["summary"] = default_attributes
nh3_attributes["span"] = default_attributes
nh3_attributes["table"] = default_attributes
nh3_attributes["code"] = {*default_attributes, "language"}
nh3_attributes["blockquote"] = {"data-line"}

nh3_attributes["img"].add("loading")
nh3_attributes["img"].add("class")
nh3_attributes["img"].add("style")
nh3_attributes["a"].add("target")
nh3_attributes["a"].add("style")
nh3_attributes["a"].add("class")


def sanitize_string(value: str) -> str:
    value = nh3.clean(value, attributes=nh3_attributes, link_rel=None)
    for key in nh3_rollback:
        value = value.replace(key, nh3_rollback[key])
    return value
