import uuid

from pydantic import BaseModel

from apps.shared.enums import Language


class FlowBase(BaseModel):
    name: str
    description: dict[Language, str]
    is_single_report: bool = False
    hide_badge: bool = False
    report_included_activity_name: str | None = None
    report_included_item_name: str | None = None
    is_hidden: bool | None = False


class FlowItemBase(BaseModel):
    activity_id: uuid.UUID
