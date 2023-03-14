import uuid

from pydantic import Field

from apps.shared.domain import InternalModel


class ActivityFlowItemCreate(InternalModel):
    activity_key: uuid.UUID


class PreparedFlowItemCreate(InternalModel):
    activity_flow_id: uuid.UUID
    activity_id: uuid.UUID


class FlowCreate(InternalModel):
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    is_single_report: bool = False
    hide_badge: bool = False
    items: list[ActivityFlowItemCreate]
    is_hidden: bool = False
