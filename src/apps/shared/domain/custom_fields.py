import mimetypes

from pydantic import BaseModel, validator
from pydantic.color import Color

__all__ = [
    "CustomColorField",
    "CustomImageField",
]


class CustomColorField(BaseModel):
    value: str

    @validator("value")
    def validate_value(cls, value):
        if type(value) is Color:
            return value.as_hex()
        raise ValueError("Not a color")


class CustomImageField(BaseModel):
    value: str

    @validator("value")
    def validate_value(cls, value):
        if (mimetypes.guess_type(value)[0] or "").startswith("image/"):
            return value
        raise ValueError("Not an image")
