import datetime
from enum import Enum

from pydantic import Field, root_validator, validator

from apps.activities.errors import IncorrectTimeRange
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


class TimePayloadType(str, Enum):
    START_TIME = "startTime"
    END_TIME = "endTime"


OPTION_BASED_CONDITIONS = [
    MultiSelectConditionType.INCLUDES_OPTION,
    MultiSelectConditionType.NOT_INCLUDES_OPTION,
    SingleSelectConditionType.EQUAL_TO_OPTION,
    SingleSelectConditionType.NOT_EQUAL_TO_OPTION,
]


class OptionPayload(PublicModel):
    option_value: str


class ValuePayload(PublicModel):
    value: float
    row_index: int | None = None

    @validator("value")
    def validate_score(cls, value):
        return round(value, 2)


class DatePayload(PublicModel):
    value: datetime.date

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d["value"] = self.value.isoformat()
        return d


class TimePayload(PublicModel):
    value: datetime.time
    type: TimePayloadType

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d["value"] = self.value.strftime("%H:%M")
        return d


class TimeRangePayload(PublicModel):
    type: str = Field(TimePayloadType.START_TIME, const=True)
    min_value: datetime.time
    max_value: datetime.time

    @root_validator
    def validate_time_range(cls, values):
        max_value = values.get("max_value")
        min_value = values.get("min_value")
        if max_value and min_value:
            if min_value > max_value:
                raise IncorrectTimeRange()
        return values


class MinMaxPayload(PublicModel):
    min_value: float
    max_value: float
    row_index: int | None = None

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
    payload: ValuePayload | DatePayload | TimePayload | TimeRangePayload


class LessThanCondition(BaseCondition):
    type: str = Field(ConditionType.LESS_THAN, const=True)
    payload: ValuePayload | DatePayload | TimePayload | TimeRangePayload


class EqualCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL, const=True)
    payload: ValuePayload | DatePayload | TimePayload | TimeRangePayload


class NotEqualCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_EQUAL, const=True)
    payload: ValuePayload | DatePayload | TimePayload | TimeRangePayload


class BetweenCondition(BaseCondition):
    type: str = Field(ConditionType.BETWEEN, const=True)
    payload: MinMaxPayload | DatePayload | TimePayload | TimeRangePayload


class OutsideOfCondition(BaseCondition):
    type: str = Field(ConditionType.OUTSIDE_OF, const=True)
    payload: MinMaxPayload | DatePayload | TimePayload | TimeRangePayload


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
