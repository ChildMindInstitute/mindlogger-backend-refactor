from enum import Enum

from pydantic import Field, PositiveInt, root_validator, validator

from apps.activities.domain.conditional_logic import Match
from apps.activities.domain.conditions import ScoreCondition, SectionCondition
from apps.activities.domain.custom_validation import (
    validate_raw_score_subscale,
    validate_score_subscale_table,
)
from apps.activities.errors import (
    DuplicateScoreConditionIdError,
    DuplicateScoreConditionNameError,
    DuplicateScoreIdError,
    DuplicateScoreItemNameError,
    DuplicateScoreNameError,
    DuplicateSectionConditionIdError,
    DuplicateSectionConditionNameError,
    DuplicateSectionNameError,
    DuplicateSubscaleNameError,
    ItemsRequiredForConditionalLogicError,
    MessageRequiredForConditionalLogicError,
    ScoreConditionItemNameError,
    SectionMessageOrItemError,
)
from apps.shared.domain import PublicModel


class CalculationType(str, Enum):
    SUM = "sum"
    AVERAGE = "average"
    PERCENTAGE = "percentage"


class ScoreConditionalLogic(PublicModel):
    name: str
    id: str
    flag_score: bool = False
    show_message: bool = False
    message: str | None = None
    print_items: bool = False
    items_print: list[str] | None = Field(default_factory=list)
    match: Match = Field(default=Match.ALL)
    conditions: list[ScoreCondition]

    @validator("message")
    def validate_message(cls, value, values):
        if values.get("show_message") and not value:
            raise MessageRequiredForConditionalLogicError()
        return value

    @validator("items_print")
    def validate_items_print(cls, value, values):
        if values.get("print_items") and not value:
            raise ItemsRequiredForConditionalLogicError()
        return value


class Score(PublicModel):
    name: str
    id: str
    calculation_type: CalculationType
    min_score: int
    max_score: int
    items_score: list[str] | None = Field(default_factory=list)
    show_message: bool = False
    message: str | None = None
    print_items: bool = False
    items_print: list[str] | None = Field(default_factory=list)
    conditional_logic: list[ScoreConditionalLogic] | None = None

    @validator("conditional_logic")
    def validate_conditional_logic(cls, value, values):
        if value:
            # check if all item names are same as values.name
            item_names = []
            for v in value:
                item_names += [
                    condition.item_name for condition in v.conditions
                ]
            if set(item_names) != {values.get("name")}:
                raise ScoreConditionItemNameError()

        return value

    @validator("items_score")
    def validate_items_score(cls, value, values):
        if value:
            # check if there are duplicate item names
            if len(value) != len(set(value)):
                raise DuplicateScoreItemNameError()

        return value

    @validator("message")
    def validate_message(cls, value, values):
        if values.get("show_message") and not value:
            raise MessageRequiredForConditionalLogicError()
        return value

    @validator("items_print")
    def validate_items_print(cls, value, values):
        if values.get("print_items") and not value:
            raise ItemsRequiredForConditionalLogicError()
        return value


class SectionConditionalLogic(PublicModel):
    name: str
    id: str
    show_message: bool = False
    message: str | None = None
    print_items: bool = False
    items_print: list[str] | None = Field(default_factory=list)
    match: Match = Field(default=Match.ALL)
    conditions: list[
        SectionCondition
    ]  # can be SingleSelection, MultiSelection, Slider, Score, ScoreCondition

    @validator("message")
    def validate_message(cls, value, values):
        if values.get("show_message") and not value:
            raise MessageRequiredForConditionalLogicError()
        return value

    @validator("items_print")
    def validate_items_print(cls, value, values):
        if values.get("print_items") and not value:
            raise ItemsRequiredForConditionalLogicError()
        return value


class Section(PublicModel):
    name: str
    show_message: bool = False
    message: str | None = None
    print_items: bool = False
    items_print: list[str] | None = Field(default_factory=list)
    conditional_logic: SectionConditionalLogic | None = None

    @root_validator()
    def validate_show_message(cls, values):
        if not values.get("show_message") and not values.get("print_items"):
            raise SectionMessageOrItemError()
        return values

    @validator("message")
    def validate_message(cls, value, values):
        if values.get("show_message") and not value:
            raise MessageRequiredForConditionalLogicError()
        return value

    @validator("items_print")
    def validate_items_print(cls, value, values):
        if values.get("print_items") and not value:
            raise ItemsRequiredForConditionalLogicError()
        return value


class ScoresAndReports(PublicModel):
    generate_report: bool = False
    show_score_summary: bool = False
    scores: list[Score] | None = Field(default_factory=list)
    sections: list[Section] | None = Field(default_factory=list)

    @validator("scores")
    def validate_scores(cls, value, values):
        if value:
            # check if there are duplicate score names and ids
            scores_names = [score.name for score in value]
            if len(scores_names) != len(set(scores_names)):
                raise DuplicateScoreNameError()
            scores_ids = [score.id for score in value]
            if len(scores_ids) != len(set(scores_ids)):
                raise DuplicateScoreIdError()
            # check if there are duplicate score condition names and ids
            score_condition_names = []
            score_condition_ids = []
            for score in value:
                if score.conditional_logic:
                    score_condition_names += [
                        logic.name for logic in score.conditional_logic
                    ]
                    score_condition_ids += [
                        logic.id for logic in score.conditional_logic
                    ]
            if len(score_condition_names) != len(set(score_condition_names)):
                raise DuplicateScoreConditionNameError()
            if len(score_condition_ids) != len(set(score_condition_ids)):
                raise DuplicateScoreConditionIdError()

        return value

    @validator("sections")
    def validate_sections(cls, value, values):
        if value:
            # check if there are duplicate section names
            section_names = [section.name for section in value]
            if len(section_names) != len(set(section_names)):
                raise DuplicateSectionNameError()
            # check if there are duplicate section condition names and ids
            section_condition_names = []
            section_condition_ids = []
            for section in value:
                if section.conditional_logic:
                    section_condition_names.append(
                        section.conditional_logic.name
                    )
                    section_condition_ids.append(section.conditional_logic.id)
            if len(section_condition_names) != len(
                set(section_condition_names)
            ):
                raise DuplicateSectionConditionNameError()
            if len(section_condition_ids) != len(set(section_condition_ids)):
                raise DuplicateSectionConditionIdError()

        return value


class SubscaleCalculationType(str, Enum):
    SUM = "sum"
    AVERAGE = "average"


class SubScaleLookupTable(PublicModel):
    score: str
    raw_score: str
    age: PositiveInt | None = None
    sex: str | None = Field(
        default=None, regex="^(M|F)$", description="M or F"
    )
    optional_text: str | None = None

    @validator("raw_score")
    def validate_raw_score_lookup(cls, value):
        return validate_raw_score_subscale(value)

    @validator("score")
    def validate_score_lookup(cls, value):
        return validate_score_subscale_table(value)


class Subscale(PublicModel):
    name: str
    scoring: SubscaleCalculationType
    items: list[str] | None = Field(default_factory=list)
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
    total_scores_table_data: list[TotalScoreTable] | None = Field(
        default_factory=list
    )

    @validator("subscales")
    def validate_unique_subscale_names(cls, value):
        if value:
            # check if there are duplicate subscale names
            subscale_names = [subscale.name for subscale in value]
            if len(subscale_names) != len(set(subscale_names)):
                raise DuplicateSubscaleNameError()

        return value
