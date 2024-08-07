from pydantic import BaseModel, Field, validator

from apps.activities.domain.response_type_config import PerformanceTaskType
from apps.activities.domain.scores_reports import ScoresAndReports, SubscaleSetting
from apps.shared.domain.custom_validations import sanitize_string
from apps.shared.enums import Language


class ActivityBase(BaseModel):
    name: str
    description: dict[Language, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    is_hidden: bool | None = False
    scores_and_reports: ScoresAndReports | None = None
    subscale_setting: SubscaleSetting | None = None
    report_included_item_name: str | None = None
    performance_task_type: PerformanceTaskType | None = None
    is_performance_task: bool = False
    auto_assign: bool | None = True

    @validator("name")
    def validate_string(cls, value):
        return sanitize_string(value)

    @validator("description")
    def validate_description(cls, value):
        if isinstance(value, dict):
            for key in value:
                value[key] = sanitize_string(value[key])
        elif isinstance(value, str):
            value = sanitize_string(value)
        return value
