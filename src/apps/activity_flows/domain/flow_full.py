import uuid

from pydantic import Field

from apps.shared.domain import InternalModel


class ActivityFlowItemFull(InternalModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    activity_flow_id: uuid.UUID
    ordering: int


class FlowFull(InternalModel):
    id: uuid.UUID
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    is_single_report: bool = False
    hide_badge: bool = False
    items: list[ActivityFlowItemFull] = Field(default_factory=list)
    is_hidden: bool = False
    ordering: int
