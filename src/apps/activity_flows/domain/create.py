import uuid

from pydantic import BaseModel, Field

__all__ = ["ActivityFlowCreate", "ActivityFlowItemCreate"]


class ActivityFlowItemCreate(BaseModel):
    activity_guid: uuid.UUID


class ActivityFlowCreate(BaseModel):
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    is_single_report: bool = False
    hide_badge: bool = False
    items: list[ActivityFlowItemCreate]
