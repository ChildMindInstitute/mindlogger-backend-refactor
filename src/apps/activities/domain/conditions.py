import datetime
from enum import Enum

from pydantic import Field, validator

from apps.shared.domain import PublicModel


class ConditionType(str, Enum):
    INCLUDES_OPTION = "INCLUDES_OPTION"
    NOT_INCLUDES_OPTION = "NOT_INCLUDES_OPTION"
    EQUAL_TO_OPTION = "EQUAL_TO_OPTION"
    NOT_EQUAL_TO_OPTION = "NOT_EQUAL_TO_OPTION"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"
    BETWEEN = "BETWEEN"
    OUTSIDE_OF = "OUTSIDE_OF"
    EQUAL_TO_SCORE = "EQUAL_TO_SCORE"


class MultiSelectConditionType(str, Enum):
    INCLUDES_OPTION = "INCLUDES_OPTION"
    NOT_INCLUDES_OPTION = "NOT_INCLUDES_OPTION"


class SingleSelectConditionType(str, Enum):
    EQUAL_TO_OPTION = "EQUAL_TO_OPTION"
    NOT_EQUAL_TO_OPTION = "NOT_EQUAL_TO_OPTION"


class SliderConditionType(str, Enum):
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"
    BETWEEN = "BETWEEN"
    OUTSIDE_OF = "OUTSIDE_OF"


class OptionPayload(PublicModel):
    option_value: str


class ValuePayload(PublicModel):
    value: float

    @validator("value")
    def validate_score(cls, value):
        return round(value, 2)


class DatePayload(PublicModel):
    value: str  # iso string

    @validator("value", pre=True)
    def validate_value(cls, value):
        # check only
        datetime.date.fromisoformat(value)
        return value


# time hh:mm
# timerange hh:mm


class MinMaxPayload(PublicModel):
    min_value: float
    max_value: float

    @validator("min_value", "max_value")
    def validate_score(cls, value):
        return round(value, 2)


class ScoreConditionPayload(PublicModel):
    value: bool


class BaseCondition(PublicModel):
    item_name: str


class IncludesOptionCondition(BaseCondition):
    type: str = Field(ConditionType.INCLUDES_OPTION, const=True)
    payload: OptionPayload


class NotIncludesOptionCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_INCLUDES_OPTION, const=True)
    payload: OptionPayload


class EqualToOptionCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL_TO_OPTION, const=True)
    payload: OptionPayload


class NotEqualToOptionCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_EQUAL_TO_OPTION, const=True)
    payload: OptionPayload


class GreaterThanCondition(BaseCondition):
    type: str = Field(ConditionType.GREATER_THAN, const=True)
    payload: ValuePayload | DatePayload


class LessThanCondition(BaseCondition):
    type: str = Field(ConditionType.LESS_THAN, const=True)
    payload: ValuePayload | DatePayload


class EqualCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL, const=True)
    payload: ValuePayload | DatePayload


class NotEqualCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_EQUAL, const=True)
    payload: ValuePayload | DatePayload


class MinMaxRowPayload(MinMaxPayload):
    row_index: int


class BetweenCondition(BaseCondition):
    type: str = Field(ConditionType.BETWEEN, const=True)
    payload: MinMaxPayload


class OutsideOfCondition(BaseCondition):
    type: str = Field(ConditionType.OUTSIDE_OF, const=True)
    payload: MinMaxPayload | MinMaxRowPayload


class ScoreBoolCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL_TO_SCORE, const=True)
    payload: ScoreConditionPayload


Condition = (
    IncludesOptionCondition
    | NotIncludesOptionCondition
    | EqualToOptionCondition
    | NotEqualToOptionCondition
    | GreaterThanCondition
    | LessThanCondition
    | EqualCondition
    | NotEqualCondition
    | BetweenCondition
    | OutsideOfCondition
)

ScoreCondition = (
    GreaterThanCondition
    | LessThanCondition
    | EqualCondition
    | NotEqualCondition
    | BetweenCondition
    | OutsideOfCondition
)
SectionCondition = (
    IncludesOptionCondition
    | NotIncludesOptionCondition
    | EqualToOptionCondition
    | NotEqualToOptionCondition
    | GreaterThanCondition
    | LessThanCondition
    | EqualCondition
    | NotEqualCondition
    | BetweenCondition
    | OutsideOfCondition
    | ScoreBoolCondition
)
AnyCondition = (
    IncludesOptionCondition
    | NotIncludesOptionCondition
    | EqualToOptionCondition
    | NotEqualToOptionCondition
    | GreaterThanCondition
    | LessThanCondition
    | EqualCondition
    | NotEqualCondition
    | BetweenCondition
    | OutsideOfCondition
    | ScoreBoolCondition
)
