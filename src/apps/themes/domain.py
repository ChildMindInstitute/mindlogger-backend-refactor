import uuid

from pydantic import BaseModel, Field
from pydantic.color import Color

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "ThemeRequest",
    "PublicTheme",
    "Theme",
    "ThemeQueryParams",
]

from pydantic import validator

from apps.shared.domain.custom_validations import (
    validate_color,
    validate_image,
)
from apps.shared.query_params import BaseQueryParams


class ThemeBase(BaseModel):
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
        return validate_image(value)

    @validator("primary_color", "secondary_color", "tertiary_color")
    def validate_color(cls, value):
        return validate_color(value)


class Theme(ThemeBase, InternalModel):
    id: uuid.UUID
    creator_id: uuid.UUID
    public: bool
    allow_rename: bool


class PublicTheme(ThemeBase, PublicModel):
    id: uuid.UUID
    public: bool
    allow_rename: bool


class ThemeRequest(ThemeBase, PublicModel):
    pass


class ThemeQueryParams(BaseQueryParams):
    public: bool | None
    allow_rename: bool | None
    creator_id: uuid.UUID | None
