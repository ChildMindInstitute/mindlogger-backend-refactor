import uuid

from pydantic import BaseModel

from apps.shared.enums import Language


class FlowBase(BaseModel):
    name: str
    description: dict[Language, str]
    is_single_report: bool = False
    hide_badge: bool = False
    is_hidden: bool | None = False


class FlowItemBase(BaseModel):
    activity_id: uuid.UUID
