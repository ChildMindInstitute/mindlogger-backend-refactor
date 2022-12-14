from pydantic import BaseModel
from pydantic.types import PositiveInt

from apps.activities.domain.constants import InputType
from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "ReusableItemChoiceCreate",
    "ReusableItemChoice",
    "PublicReusableItemChoice",
    "ReusableItemChoiceInitializeCreate",
]


class _ReusableItemChoiceBase(BaseModel):
    token_name: str
    token_value: int
    input_type: InputType

    def __str__(self) -> str:
        return f"{self.token_name}: {self.token_value}"


class PublicReusableItemChoice(_ReusableItemChoiceBase, PublicModel):
    """Public item template data model."""

    id: PositiveInt


class ReusableItemChoiceInitializeCreate(
    _ReusableItemChoiceBase, InternalModel
):
    pass


class ReusableItemChoiceCreate(_ReusableItemChoiceBase, InternalModel):
    user_id: PositiveInt


class ReusableItemChoice(ReusableItemChoiceCreate, InternalModel):
    id: PositiveInt
