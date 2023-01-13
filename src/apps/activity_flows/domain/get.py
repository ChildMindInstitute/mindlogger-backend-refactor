import uuid

from pydantic import Field

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "ActivityFlow",
    "ActivityFlowItem",
    "PublicActivityFlow",
    "PublicActivityFlowItem",
]


class ActivityFlowItem(InternalModel):
    id: int
    activity_flow_id: int
    activity_id: int
    ordering: int


class PublicActivityFlowItem(PublicModel):
    id: int
    activity_flow_id: int
    activity_id: int
    ordering: int


class ActivityFlow(InternalModel):
    id: int
    guid: uuid.UUID
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    ordering: int
    items: list[ActivityFlowItem] = Field(default_factory=list)


class PublicActivityFlow(PublicModel):
    id: int
    guid: uuid.UUID
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    items: list[PublicActivityFlowItem] = Field(default_factory=list)
