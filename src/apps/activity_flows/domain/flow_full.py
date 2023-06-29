import uuid
from datetime import datetime

from pydantic import Field

from apps.activity_flows.domain.base import FlowBase, FlowItemBase
from apps.shared.domain import InternalModel, PublicModel


class ActivityFlowItemFull(FlowItemBase, InternalModel):
    id: uuid.UUID
    activity_flow_id: uuid.UUID
    order: int


class FlowItemHistoryFull(InternalModel):
    id: uuid.UUID
    activity_flow_id: str
    activity_id: str
    order: int


class FlowFull(FlowBase, InternalModel):
    id: uuid.UUID
    items: list[ActivityFlowItemFull] = Field(default_factory=list)
    order: int
    created_at: datetime


class FlowHistoryFull(FlowBase, InternalModel):
    id: uuid.UUID
    id_version: str
    items: list[FlowItemHistoryFull] = Field(default_factory=list)
    order: int
    created_at: datetime


class PublicActivityFlowItemFull(FlowItemBase, PublicModel):
    id: uuid.UUID
    order: int


class PublicFlowFull(FlowBase, PublicModel):
    id: uuid.UUID
    items: list[PublicActivityFlowItemFull] = Field(default_factory=list)
    order: int
    created_at: datetime
