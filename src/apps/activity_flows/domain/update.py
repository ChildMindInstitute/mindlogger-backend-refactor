import pydantic.types as types
from pydantic import BaseModel

__all__ = ["ActivityFlowUpdate", "ActivityFlowItemUpdate"]


class ActivityFlowItemUpdate(BaseModel):
    id: int | None = None
    activity_guid: types.UUID4


class ActivityFlowUpdate(BaseModel):
    id: int
    name: str
    description: types.Dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    items: types.List[ActivityFlowItemUpdate]
