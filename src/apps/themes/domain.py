import mimetypes
import uuid

from pydantic import BaseModel, Field, validator
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
    name: str = Field(
        ...,
        description="Name of the theme",
        example="My theme",
        max_length=100,
    )
    logo: str = Field(
        ...,
        description="URL to logo image",
        example="https://example.com/logo.png",
    )
    background_image: str = Field(
        ...,
        description="URL to background image",
        example="https://example.com/background.png",
    )
    primary_color: Color = Field(
        ...,
        description="Primary color",
        example="#FFFFFF",
    )
    secondary_color: Color = Field(
        ...,
        description="Secondary color",
        example="#FFFFFF",
    )
    tertiary_color: Color = Field(
        ...,
        description="Tertiary color",
        example="#FFFFFF",
    )

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
