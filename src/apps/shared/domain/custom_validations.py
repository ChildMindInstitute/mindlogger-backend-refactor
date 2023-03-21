import mimetypes

from pydantic.color import Color

__all__ = [
    "validate_image",
    "validate_color",
]


def validate_image(value: str) -> str:
    if (mimetypes.guess_type(value)[0] or "").startswith("image/"):
        return value
    raise ValueError("Not an image")


def validate_color(value: str | Color) -> str:
    if type(value) is Color:
        return value.as_hex()
    raise ValueError("Not a color")
