from pydantic import BaseModel, Field

from apps.shared.enums import Language


class Score(BaseModel):
    score_name: str
    score_id: str
    calculation_type: str
    range_of_scores: str
    items: list[str] | None = Field(default_factory=list)
    show_message: bool = False
    message: str = ""
    print_items: bool = False


class Section(BaseModel):
    pass


class ScoresAndReports(BaseModel):
    generate_report: bool = False
    show_score_summary: bool = False
    scores: list[Score] | None = Field(default_factory=list)
    sections: list[Section] | None = Field(default_factory=list)


class Subscale(BaseModel):
    pass


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
