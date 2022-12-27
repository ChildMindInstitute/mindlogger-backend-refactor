import pydantic.types as types
from pydantic import BaseModel

__all__ = ["ActivityFlowCreate", "ActivityFlowItemCreate"]


class ActivityFlowItemCreate(BaseModel):
    activity_guid: types.UUID4


class ActivityFlowCreate(BaseModel):
    name: str
    description: types.Dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    items: types.List[ActivityFlowItemCreate]
