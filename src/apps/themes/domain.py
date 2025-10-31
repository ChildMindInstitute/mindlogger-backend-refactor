import uuid

from pydantic import field_validator, BaseModel, Field

from apps.shared.domain import InternalModel, PublicModel
from pydantic_extra_types.color import Color

__all__ = [
    "ThemeRequest",
    "PublicTheme",
    "Theme",
    "ThemeQueryParams",
]

from apps.shared.domain.custom_validations import validate_color, validate_image
from apps.shared.query_params import BaseQueryParams


class ThemeBase(BaseModel):
    name: str = Field(
        ...,
        description="Name of the theme",
        examples=["My theme"],
        max_length=100,
    )
    logo: str | None = Field(
        ...,
        description="URL to logo image",
        examples=["https://example.com/logo.png"],
    )
    background_image: str | None = Field(
        ...,
        description="URL to background image",
        examples=["https://example.com/background.png"],
    )
    primary_color: Color = Field(
        ...,
        description="Primary color",
        examples=["#FFFFFF"],
    )
    secondary_color: Color = Field(
        ...,
        description="Secondary color",
        examples=["#FFFFFF"],
    )
    tertiary_color: Color = Field(
        ...,
        description="Tertiary color",
        examples=["#FFFFFF"],
    )

    def __str__(self) -> str:
        return self.name

    @field_validator("logo", "background_image")
    @classmethod
    def validate_image(cls, value):
        return validate_image(value) if value else value

    @field_validator("primary_color", "secondary_color", "tertiary_color")
    @classmethod
    def validate_color(cls, value):
        return validate_color(value) if value else value


class Theme(ThemeBase, InternalModel):
    id: uuid.UUID
    creator_id: uuid.UUID | None = None
    public: bool
    allow_rename: bool


class PublicTheme(ThemeBase, PublicModel):
    id: uuid.UUID
    public: bool
    allow_rename: bool


class PublicThemeMobile(PublicModel):
    id: uuid.UUID
    name: str = Field(
        ...,
        description="Name of the theme",
        examples=["My theme"],
        max_length=100,
    )
    logo: str | None = Field(
        ...,
        description="URL to logo image",
        examples=["https://example.com/logo.png"],
    )
    background_image: str | None = Field(
        ...,
        description="URL to background image",
        examples=["https://example.com/background.png"],
    )
    primary_color: Color = Field(
        ...,
        description="Primary color",
        examples=["#FFFFFF"],
    )
    secondary_color: Color = Field(
        ...,
        description="Secondary color",
        examples=["#FFFFFF"],
    )
    tertiary_color: Color = Field(
        ...,
        description="Tertiary color",
        examples=["#FFFFFF"],
    )

    def __str__(self) -> str:
        return self.name

    @field_validator("logo", "background_image")
    @classmethod
    def validate_image(cls, value):
        return validate_image(value) if value else value

    @field_validator("primary_color", "secondary_color", "tertiary_color")
    @classmethod
    def validate_color(cls, value):
        return validate_color(value) if value else value


class ThemeRequest(ThemeBase, PublicModel):
    pass


class ThemeQueryParams(BaseQueryParams):
    public: bool | None
    allow_rename: bool | None
    creator_id: uuid.UUID | None
