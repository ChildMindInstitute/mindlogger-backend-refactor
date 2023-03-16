import uuid

from pydantic import Field

from apps.shared.domain import InternalModel


class ActivityFlowItemUpdate(InternalModel):
    id: uuid.UUID | None
    activity_key: uuid.UUID


class PreparedFlowItemUpdate(InternalModel):
    id: uuid.UUID | None
    activity_flow_id: uuid.UUID
    activity_id: uuid.UUID


class FlowUpdate(InternalModel):
    id: uuid.UUID | None
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    is_single_report: bool = False
    hide_badge: bool = False
    items: list[ActivityFlowItemUpdate]
    is_hidden: bool = False
