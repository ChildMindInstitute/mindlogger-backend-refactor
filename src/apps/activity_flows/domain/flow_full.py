import uuid

from pydantic import Field

from apps.activity_flows.domain.base import FlowBase, FlowItemBase
from apps.shared.domain import InternalModel, PublicModel


class ActivityFlowItemFull(FlowItemBase, InternalModel):
    id: uuid.UUID
    activity_flow_id: uuid.UUID
    order: int


class FlowFull(FlowBase, InternalModel):
    id: uuid.UUID
    items: list[ActivityFlowItemFull] = Field(default_factory=list)
    order: int


class PublicActivityFlowItemFull(FlowItemBase, PublicModel):
    id: uuid.UUID
    order: int


class PublicFlowFull(FlowBase, PublicModel):
    id: uuid.UUID
    items: list[PublicActivityFlowItemFull] = Field(default_factory=list)
    order: int
