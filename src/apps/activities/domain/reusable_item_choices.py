import uuid

from pydantic import Field, BaseModel

from apps.activities.domain.constants import InputType
from apps.shared.domain import InternalModel, PublicModel
from typing_extensions import Annotated

__all__ = [
    "ReusableItemChoiceCreate",
    "ReusableItemChoice",
    "PublicReusableItemChoice",
    "ReusableItemChoiceInitializeCreate",
]


class _ReusableItemChoiceBase(BaseModel):
    token_name: str
    token_value: Annotated[int, Field(gt=-2147483648, lt=2147483647)]  # type: ignore
    input_type: InputType


class PublicReusableItemChoice(_ReusableItemChoiceBase, PublicModel):
    """Public item template data model."""

    id: uuid.UUID


class ReusableItemChoiceInitializeCreate(_ReusableItemChoiceBase, InternalModel):
    pass


class ReusableItemChoiceCreate(_ReusableItemChoiceBase, InternalModel):
    user_id: uuid.UUID


class ReusableItemChoice(ReusableItemChoiceCreate, InternalModel):
    id: uuid.UUID
