import mimetypes
import uuid

from pydantic import BaseModel, validator
from pydantic.color import Color

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "ThemeRequest",
    "ThemeCreate",
    "PublicTheme",
    "Theme",
    "ThemeUpdate",
    "ThemeQueryParams",
]

from apps.shared.query_params import BaseQueryParams


class _ThemeBase(BaseModel):
    name: str
    logo: str
    background_image: str
    primary_color: Color
    secondary_color: Color
    tertiary_color: Color

    def __str__(self) -> str:
        return self.name

    @validator("logo", "background_image")
    def validate_image(cls, value):
        if (mimetypes.guess_type(value)[0] or "").startswith("image/"):
            return value
        raise ValueError("Not an image")

    @validator("primary_color", "secondary_color", "tertiary_color")
    def validate_color(cls, value):
        if type(value) is Color:
            return value.as_hex()
        raise ValueError("Not a color")


class ThemeRequest(_ThemeBase, PublicModel):
    pass


class ThemeUpdate(_ThemeBase, InternalModel):
    public: bool
    allow_rename: bool


class ThemeCreate(ThemeUpdate, InternalModel):
    creator_id: uuid.UUID


class PublicTheme(_ThemeBase, PublicModel):
    """Public theme model."""

    id: uuid.UUID


class Theme(ThemeCreate):
    id: uuid.UUID


class ThemeQueryParams(BaseQueryParams):
    public: bool | None = None
    allow_rename: bool | None = None
    creator_id: uuid.UUID | None = None
