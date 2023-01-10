import uuid

from pydantic import BaseModel

__all__ = ["ActivityFlowUpdate", "ActivityFlowItemUpdate"]


class ActivityFlowItemUpdate(BaseModel):
    id: int | None = None
    activity_guid: uuid.UUID


class ActivityFlowUpdate(BaseModel):
    id: int | None
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    items: list[ActivityFlowItemUpdate]
