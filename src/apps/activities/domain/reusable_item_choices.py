import uuid

from pydantic import BaseModel, conint

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
    token_value: conint(gt=-2147483648, lt=2147483647)  # type: ignore
    input_type: InputType


class PublicReusableItemChoice(_ReusableItemChoiceBase, PublicModel):
    """Public item template data model."""

    id: uuid.UUID


class ReusableItemChoiceInitializeCreate(
    _ReusableItemChoiceBase, InternalModel
):
    pass


class ReusableItemChoiceCreate(_ReusableItemChoiceBase, InternalModel):
    user_id: uuid.UUID


class ReusableItemChoice(ReusableItemChoiceCreate, InternalModel):
    id: uuid.UUID
