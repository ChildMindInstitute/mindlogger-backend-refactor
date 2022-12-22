from pydantic import BaseModel
from pydantic.types import PositiveInt

from apps.items.domain.constants import InputType
from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "ItemTemplateCreate",
    "ItemTemplate",
]


class _ItemTemplateBase(BaseModel):
    token_name: str
    token_value: int
    input_type: InputType

    def __str__(self) -> str:
        return f"{self.token_name}: {self.token_value}"


class PublicItemTemplate(_ItemTemplateBase, PublicModel):
    """Public item template data model."""

    id: PositiveInt


class ItemTemplateInitializeCreate(_ItemTemplateBase, InternalModel):
    pass


class ItemTemplateCreate(_ItemTemplateBase, InternalModel):
    user_id: PositiveInt


class ItemTemplate(ItemTemplateCreate, InternalModel):
    id: PositiveInt
