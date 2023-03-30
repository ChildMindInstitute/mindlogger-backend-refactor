import uuid

from pydantic import Field

from apps.shared.domain import InternalModel, PublicModel


class Flow(InternalModel):
    id: uuid.UUID
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    order: int
    is_hidden: bool | None = False


class FlowPublic(PublicModel):
    id: uuid.UUID
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    order: int
    is_hidden: bool | None = False


class FlowDetail(Flow):
    description: str  # type: ignore[assignment]
    activity_ids: list[uuid.UUID] = Field(default_factory=list)


class FlowDuplicate(Flow):
    activity_ids: list[uuid.UUID] = Field(default_factory=list)


class FlowDetailPublic(FlowPublic):
    description: str  # type: ignore[assignment]
    activity_ids: list[uuid.UUID] = Field(default_factory=list)
