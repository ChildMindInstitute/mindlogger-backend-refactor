import uuid
from datetime import datetime

from pydantic import Field

from apps.activity_flows.domain.base import FlowBase
from apps.shared.domain import InternalModel, PublicModel


class Flow(FlowBase, InternalModel):
    id: uuid.UUID
    applet_id: uuid.UUID
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


class FlowSingleLanguageMobileDetailPublic(InternalModel):
    id: uuid.UUID
    name: str
    description: str
    hide_badge: bool = False
    is_single_report: bool = False
    order: int
    is_hidden: bool | None = False
    activity_ids: list[uuid.UUID] = Field(default_factory=list)


class FlowDuplicate(FlowBase, InternalModel):
    id: uuid.UUID
    order: int
    activity_ids: list[uuid.UUID] = Field(default_factory=list)
