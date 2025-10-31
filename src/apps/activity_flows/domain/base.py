import uuid

from pydantic import field_validator, BaseModel

from apps.shared.domain.custom_validations import sanitize_string
from apps.shared.enums import Language


class FlowBase(BaseModel):
    name: str
    description: dict[Language, str]
    is_single_report: bool = False
    hide_badge: bool = False
    report_included_activity_name: str | None = None
    report_included_item_name: str | None = None
    is_hidden: bool | None = False
    auto_assign: bool | None = True

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        if isinstance(value, dict):
            for key in value:
                value[key] = sanitize_string(value[key])
        elif isinstance(value, str):
            value = sanitize_string(value)
        return value

    @field_validator("name")
    @classmethod
    def validate_string(cls, value):
        return sanitize_string(value)


class FlowItemBase(BaseModel):
    activity_id: uuid.UUID
