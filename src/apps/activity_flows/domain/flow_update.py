import uuid

from apps.activity_flows.domain.base import FlowBase
from apps.shared.domain import InternalModel


class ActivityFlowItemUpdate(InternalModel):
    id: uuid.UUID | None
    activity_key: uuid.UUID


class PreparedFlowItemUpdate(InternalModel):
    id: uuid.UUID | None
    activity_flow_id: uuid.UUID
    activity_id: uuid.UUID


class FlowUpdate(FlowBase, InternalModel):
    id: uuid.UUID | None
    items: list[ActivityFlowItemUpdate]
