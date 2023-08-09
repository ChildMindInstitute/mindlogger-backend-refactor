from pydantic import BaseModel, Field

from apps.activities.domain.scores_reports import (
    ScoresAndReports,
    SubscaleSetting,
)
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
