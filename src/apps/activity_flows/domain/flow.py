import uuid
from datetime import datetime

from pydantic import Field

from apps.activity_flows.domain.base import FlowBase
from apps.shared.domain import InternalModel, PublicModel


class Flow(FlowBase, InternalModel):
    id: uuid.UUID
    order: int


class FlowPublic(FlowBase, PublicModel):
    id: uuid.UUID
    order: int


class FlowSingleLanguageDetail(FlowBase, InternalModel):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    activity_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime


class FlowSingleLanguageDetailPublic(FlowPublic):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    activity_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime


class FlowDuplicate(FlowBase, InternalModel):
    id: uuid.UUID
    order: int
    activity_ids: list[uuid.UUID] = Field(default_factory=list)
