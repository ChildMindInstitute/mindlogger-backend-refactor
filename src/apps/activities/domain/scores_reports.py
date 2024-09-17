import enum
from enum import Enum

from pydantic import Field, PositiveInt, validator

from apps.activities.domain.conditional_logic import Match
from apps.activities.domain.conditions import ScoreCondition, SectionCondition
from apps.activities.domain.custom_validation_subscale import validate_raw_score_subscale, \
    validate_score_subscale_table, validate_age_subscale
from apps.activities.errors import (
    DuplicateScoreConditionIdError,
    DuplicateScoreConditionNameError,
    DuplicateScoreIdError,
    DuplicateScoreItemNameError,
    DuplicateScoreNameError,
    DuplicateSectionNameError,
    DuplicateSubscaleNameError,
    ScoreConditionItemNameError,
)
from apps.shared.domain import PublicModel
from apps.shared.domain.custom_validations import sanitize_string


class CalculationType(str, Enum):
    SUM = "sum"
    AVERAGE = "average"
    PERCENTAGE = "percentage"


class ScoreConditionalLogic(PublicModel):
    name: str
    id: str
    flag_score: bool = False
    message: str | None = None
    items_print: list[str] | None = Field(default_factory=list)
    match: Match = Field(default=Match.ALL)
    conditions: list[ScoreCondition]

    @validator("message")
    def validate_string(cls, value):
        if value is not None:
            return sanitize_string(value)
        return value


class ReportType(str, enum.Enum):
    score = "score"
    section = "section"


class Score(PublicModel):
    type: str = Field(ReportType.score, const=True)
    name: str
    id: str
    calculation_type: CalculationType
    items_score: list[str] | None = Field(default_factory=list)
    message: str | None = None
    items_print: list[str] | None = Field(default_factory=list)
    conditional_logic: list[ScoreConditionalLogic] | None = None

    @validator("conditional_logic")
    def validate_conditional_logic(cls, value, values):
        if value:
            # check if all item names are same as values.id
            item_names = []
            for v in value:
                item_names += [condition.item_name for condition in v.conditions]
            if set(item_names) != {values.get("id")}:
                raise ScoreConditionItemNameError()

        return value

    @validator("items_score")
    def validate_items_score(cls, value):
        if value:
            # check if there are duplicate item names
            if len(value) != len(set(value)):
                raise DuplicateScoreItemNameError()

        return value

    @validator("message")
    def validate_string(cls, value):
        if value is not None:
            return sanitize_string(value)
        return value


class SectionConditionalLogic(PublicModel):
    match: Match = Field(default=Match.ALL)
    conditions: list[SectionCondition]  # can be SingleSelection, MultiSelection, Slider, Score, ScoreCondition


class Section(PublicModel):
    type: str = Field(ReportType.section, const=True)
    name: str
    message: str | None = None
    items_print: list[str] | None = Field(default_factory=list)
    conditional_logic: SectionConditionalLogic | None = None

    @validator("message")
    def validate_string(cls, value):
        if value is not None:
            return sanitize_string(value)
        return value


class ScoresAndReports(PublicModel):
    generate_report: bool = False
    show_score_summary: bool = False
    reports: list[Score | Section] | None = Field(default_factory=list)

    @validator("reports")
    def validate_reports(cls, value):
        scores_flt = filter(lambda v: v.type == ReportType.score, value)
        sections_flt = filter(lambda v: v.type == ReportType.section, value)
        cls.__validate_scores(list(scores_flt))
        cls.__validate_sections(list(sections_flt))
        return value

    @classmethod
    def __validate_scores(cls, value):  # noqa
        if value:
            # check if there are duplicate score names and ids
            scores_names = [score.name for score in value]
            if len(scores_names) != len(set(scores_names)):
                raise DuplicateScoreNameError()
            scores_ids = [score.id for score in value]
            if len(scores_ids) != len(set(scores_ids)):
                raise DuplicateScoreIdError()
            # check if there are duplicate score condition names and ids
            score_condition_ids = []
            for score in value:
                score_condition_names = []
                if score.conditional_logic:
                    score_condition_names += [logic.name for logic in score.conditional_logic]
                    score_condition_ids += [logic.id for logic in score.conditional_logic]
                if len(score_condition_names) != len(set(score_condition_names)):
                    raise DuplicateScoreConditionNameError()
            if len(score_condition_ids) != len(set(score_condition_ids)):
                raise DuplicateScoreConditionIdError()

        return value

    @classmethod
    def __validate_sections(cls, value):  # noqa
        if value:
            # check if there are duplicate section names
            section_names = [section.name for section in value]
            if len(section_names) != len(set(section_names)):
                raise DuplicateSectionNameError()

        return value


class ScoreConditionalLogicMobile(PublicModel):
    id: str
    name: str
    flag_score: bool = False
    match: Match = Field(default=Match.ALL)
    conditions: list[ScoreCondition]


class SubscaleCalculationType(str, Enum):
    SUM = "sum"
    AVERAGE = "average"


class SubScaleLookupTable(PublicModel):
    score: str
    raw_score: str
    age: str | None = None
    sex: str | None = Field(default=None, regex="^(M|F)$", description="M or F")
    optional_text: str | None = None
    severity: str | None = Field(default=None, regex="^(Minimal|Mild|Moderate|Severe)$")

    @validator("raw_score")
    def validate_raw_score_lookup(cls, value):
        return validate_raw_score_subscale(value)

    @validator("score")
    def validate_score_lookup(cls, value):
        return validate_score_subscale_table(value)

    @validator("age")
    def validate_age_lookup(cls, value):
        return validate_age_subscale(value)


class SubscaleItemType(str, Enum):
    ITEM = "item"
    SUBSCALE = "subscale"


class SubscaleItem(PublicModel):
    name: str
    type: SubscaleItemType


class Subscale(PublicModel):
    name: str
    scoring: SubscaleCalculationType
    items: list[SubscaleItem] | None = Field(default_factory=list)
    subscale_table_data: list[SubScaleLookupTable] | None = None


class TotalScoreTable(PublicModel):
    raw_score: str
    optional_text: str | None = None

    @validator("raw_score")
    def validate_raw_score(cls, value):
        return validate_raw_score_subscale(value)


class SubscaleSetting(PublicModel):
    calculate_total_score: SubscaleCalculationType | None = None
    subscales: list[Subscale] | None = Field(default_factory=list)
    total_scores_table_data: list[TotalScoreTable] | None = Field(default_factory=list)

    @validator("subscales")
    def validate_unique_subscale_names(cls, value):
        if value:
            # check if there are duplicate subscale names
            subscale_names = [subscale.name for subscale in value]
            if len(subscale_names) != len(set(subscale_names)):
                raise DuplicateSubscaleNameError()

        return value
