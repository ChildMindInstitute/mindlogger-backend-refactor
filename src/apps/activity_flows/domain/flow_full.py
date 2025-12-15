import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field

from apps.activities.domain import ActivityHistoryFull
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
    id_version: str
    order: int
    name: str | None = None


class FlowItemHistoryWithActivityFull(FlowItemHistoryFull):
    activity: ActivityHistoryFull | None = None


class FlowFull(FlowBase, InternalModel):
    id: uuid.UUID
    items: Annotated[list[ActivityFlowItemFull], Field(default_factory=list)]
    order: int
    created_at: datetime


class FlowHistoryBase(FlowBase):
    id: uuid.UUID
    id_version: str
    order: int
    created_at: datetime


class FlowHistoryFull(FlowHistoryBase, InternalModel):
    items: Annotated[list[FlowItemHistoryFull], Field(default_factory=list)]


class FlowHistoryWithActivityFull(FlowHistoryBase, InternalModel):
    items: Annotated[list[FlowItemHistoryWithActivityFull], Field(default_factory=list)]


class FlowHistoryWithActivityFlat(FlowHistoryBase, InternalModel):
    activities: Annotated[list[ActivityHistoryFull], Field(default_factory=list)]


class PublicActivityFlowItemFull(FlowItemBase, PublicModel):
    id: uuid.UUID
    order: int


class PublicFlowFull(FlowBase, PublicModel):
    id: uuid.UUID
    items: Annotated[list[PublicActivityFlowItemFull], Field(default_factory=list)]
    order: int
    created_at: datetime
