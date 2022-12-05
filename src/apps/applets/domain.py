from pydantic import BaseModel
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "AppletCreateRequest",
    "AppletCreate",
    "AppletUpdate",
    "Applet",
    "PublicApplet",
]


class _AppletBase(BaseModel):
    display_name: str

    def __str__(self) -> str:
        return self.display_name


class AppletCreateRequest(_AppletBase, PublicModel):
    description: str


class PublicApplet(_AppletBase, PublicModel):
    """Public user data model."""

    id: PositiveInt


class AppletCreate(_AppletBase, InternalModel):
    description: str


class AppletUpdate(_AppletBase, InternalModel):
    description: str


class Applet(AppletCreate):
    id: PositiveInt
