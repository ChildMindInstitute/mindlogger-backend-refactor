import uuid

from pydantic import BaseModel, Field

from apps.shared.domain import (
    CustomColorField,
    CustomImageField,
    InternalModel,
    PublicModel,
)

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
    logo: CustomImageField = Field(
        ...,
        description="URL to logo image",
        example="https://example.com/logo.png",
    )
    background_image: CustomImageField = Field(
        ...,
        description="URL to background image",
        example="https://example.com/background.png",
    )
    primary_color: CustomColorField = Field(
        ...,
        description="Primary color",
        example="#FFFFFF",
    )
    secondary_color: CustomColorField = Field(
        ...,
        description="Secondary color",
        example="#FFFFFF",
    )
    tertiary_color: CustomColorField = Field(
        ...,
        description="Tertiary color",
        example="#FFFFFF",
    )

    def __str__(self) -> str:
        return self.name


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
