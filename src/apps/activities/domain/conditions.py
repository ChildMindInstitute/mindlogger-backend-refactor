import datetime
from enum import Enum

from pydantic import Field, root_validator, validator

from apps.activities.errors import IncorrectTimeRange
from apps.shared.domain import PublicModel, PublicModelNoExtra


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


class OptionPayload(PublicModelNoExtra):
    option_value: str


class OptionIndexPayload(OptionPayload):
    row_index: int


class ValuePayload(PublicModelNoExtra):
    value: float

    @validator("value")
    def validate_score(cls, value):
        return round(value, 2)


class ValueIndexPayload(ValuePayload):
    row_index: int


class DatePayload(PublicModel):
    value: datetime.date

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d["value"] = self.value.isoformat()
        return d


class TimePayload(PublicModel):
    type: str | None = None
    value: datetime.time

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d["value"] = self.value.strftime("%H:%M")
        return d


class TimeRangePayload(PublicModel):
    type: TimePayloadType
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

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d["min_value"] = self.min_value.strftime("%H:%M")
        d["max_value"] = self.min_value.strftime("%H:%M")
        return d


class MinMaxPayload(PublicModelNoExtra):
    min_value: float
    max_value: float

    @validator("min_value", "max_value")
    def validate_score(cls, value):
        return round(value, 2)


class MinMaxPayloadRow(MinMaxPayload):
    row_index: int


class ScoreConditionPayload(PublicModel):
    value: bool


class BaseCondition(PublicModel):
    item_name: str


class _IncludesOptionCondition(BaseCondition):
    type: str = Field(ConditionType.INCLUDES_OPTION, const=True)


class _NotIncludesOptionCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_INCLUDES_OPTION, const=True)


class _EqualToOptionCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL_TO_OPTION, const=True)


class _NotEqualToOptionCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_EQUAL_TO_OPTION, const=True)


class _GreaterThanCondition(BaseCondition):
    type: str = Field(ConditionType.GREATER_THAN, const=True)


class _LessThanCondition(BaseCondition):
    type: str = Field(ConditionType.LESS_THAN, const=True)


class _EqualCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL, const=True)


class _NotEqualCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_EQUAL, const=True)


class _BetweenCondition(BaseCondition):
    type: str = Field(ConditionType.BETWEEN, const=True)


class _OutsideOfCondition(BaseCondition):
    type: str = Field(ConditionType.OUTSIDE_OF, const=True)


class IncludesOptionCondition(_IncludesOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class NotIncludesOptionCondition(_NotIncludesOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class EqualToOptionCondition(_EqualToOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class NotEqualToOptionCondition(_NotEqualToOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class GreaterThanCondition(_GreaterThanCondition):
    payload: ValuePayload | DatePayload | TimePayload | TimeRangePayload


class LessThanCondition(_LessThanCondition):
    payload: ValuePayload | ValueIndexPayload | DatePayload | TimePayload | TimeRangePayload


class EqualCondition(_EqualCondition):
    payload: ValuePayload | ValueIndexPayload | DatePayload | TimePayload | TimeRangePayload


class NotEqualCondition(_NotEqualCondition):
    payload: ValuePayload | ValueIndexPayload | DatePayload | TimePayload | TimeRangePayload


class BetweenCondition(_BetweenCondition):
    payload: MinMaxPayload | MinMaxPayloadRow | DatePayload | TimePayload | TimeRangePayload


class OutsideOfCondition(_OutsideOfCondition):
    payload: MinMaxPayload | MinMaxPayloadRow | DatePayload | TimePayload | TimeRangePayload


class ScoreBoolCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL_TO_SCORE, const=True)
    payload: ScoreConditionPayload


class ScoreGraterThanCondition(_GreaterThanCondition):
    payload: ValuePayload


class ScoreLessThanCondition(_LessThanCondition):
    payload: ValuePayload


class ScoreEqualCondition(_EqualCondition):
    payload: ValuePayload


class ScoreNotEqualCondition(_NotEqualCondition):
    payload: ValuePayload


class ScoreBetweenCondition(_BetweenCondition):
    payload: MinMaxPayload


class ScoreOutsideOfCondition(_OutsideOfCondition):
    payload: MinMaxPayload


class ScoreNotIncludesOptionCondition(_NotIncludesOptionCondition):
    payload: OptionPayload


class ScoreIncludesOptionCondition(_IncludesOptionCondition):
    payload: OptionPayload


class ScoreEqualToOptionCondition(_EqualToOptionCondition):
    payload: OptionPayload


class ScoreNotEqualToOptionCondition(_NotEqualToOptionCondition):
    payload: OptionPayload


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
    ScoreGraterThanCondition
    | ScoreLessThanCondition
    | ScoreEqualCondition
    | ScoreNotEqualCondition
    | ScoreBetweenCondition
    | ScoreOutsideOfCondition
)
SectionCondition = (
    ScoreIncludesOptionCondition
    | ScoreNotIncludesOptionCondition
    | ScoreEqualToOptionCondition
    | ScoreNotEqualToOptionCondition
    | ScoreGraterThanCondition
    | ScoreGraterThanCondition
    | ScoreEqualCondition
    | ScoreNotEqualCondition
    | ScoreBetweenCondition
    | ScoreOutsideOfCondition
    | ScoreBoolCondition
)
AnyCondition = (
    ScoreIncludesOptionCondition
    | ScoreNotIncludesOptionCondition
    | ScoreEqualToOptionCondition
    | ScoreNotEqualToOptionCondition
    | ScoreGraterThanCondition
    | ScoreGraterThanCondition
    | ScoreEqualCondition
    | ScoreNotEqualCondition
    | ScoreBetweenCondition
    | ScoreOutsideOfCondition
    | ScoreBoolCondition
)
