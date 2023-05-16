import mimetypes
from gettext import gettext as _

from pydantic.color import Color

__all__ = [
    "validate_image",
    "validate_color",
    "validate_audio",
    "extract_history_version",
]

from apps.shared.exception import ValidationError


class InvalidImageError(ValidationError):
    message = _("Invalid image.")


class InvalidColorError(ValidationError):
    message = _("Invalid color.")


class InvalidAudioError(ValidationError):
    message = _("Invalid audio file.")


def validate_image(value: str) -> str:
    if (mimetypes.guess_type(value)[0] or "").startswith("image/"):
        return value
    raise InvalidImageError()


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
