import mimetypes

from pydantic.color import Color

__all__ = [
    "validate_image",
    "validate_color",
    "validate_audio",
]


def validate_image(value: str) -> str:
    if (mimetypes.guess_type(value)[0] or "").startswith("image/"):
        return value
    raise ValueError("Not an image")


def validate_color(value: str | Color) -> str:
    if type(value) is Color:
        return value.as_hex()
    raise ValueError("Not a color")


def validate_audio(value: str) -> str:
    # validate file format is mp3 or wav
    if (
        (mimetypes.guess_type(value)[0] or "").startswith("audio/mpeg")
        or (mimetypes.guess_type(value)[0] or "").startswith("audio/wav")
        or (mimetypes.guess_type(value)[0] or "").startswith("audio/x-wav")
        or (mimetypes.guess_type(value)[0] or "").startswith("audio/x-pn-wav")
        or (mimetypes.guess_type(value)[0] or "").startswith("audio/wave")
    ):
        return value
    raise ValueError("Not an audio file")
