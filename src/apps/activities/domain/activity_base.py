from pydantic import BaseModel, Field

from apps.activities.domain.scores_reports import ScoresAndReports, Subscale
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
    is_hidden: bool = False
    scores_and_reports: ScoresAndReports | None = None
    subscales: list[Subscale] | None = Field(default_factory=list)
    is_assessment: bool = False
