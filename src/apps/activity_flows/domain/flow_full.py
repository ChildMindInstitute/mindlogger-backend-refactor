import uuid

from pydantic import Field

from apps.shared.domain import InternalModel, PublicModel
from apps.shared.enums import Language


class ActivityFlowItemFull(InternalModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    activity_flow_id: uuid.UUID
    order: int


class FlowFull(InternalModel):
    id: uuid.UUID
    name: str
    description: dict[Language, str] = Field(default_factory=dict)
    is_single_report: bool = False
    hide_badge: bool = False
    items: list[ActivityFlowItemFull] = Field(default_factory=list)
    is_hidden: bool | None = False
    order: int


class PublicActivityFlowItemFull(InternalModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    order: int


class PublicFlowFull(PublicModel):
    id: uuid.UUID
    name: str
    description: dict[Language, str] = Field(default_factory=dict)
    is_single_report: bool = False
    hide_badge: bool = False
    items: list[PublicActivityFlowItemFull] = Field(default_factory=list)
    is_hidden: bool = False
    order: int
