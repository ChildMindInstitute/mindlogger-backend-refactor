import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field, root_validator, validator

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


class DateConditionType(str, Enum):
    GREATER_THAN_DATE = "GREATER_THAN_DATE"
    LESS_THAN_DATE = "LESS_THAN_DATE"
    EQUAL_TO_DATE = "EQUAL_TO_DATE"
    NOT_EQUAL_TO_DATE = "NOT_EQUAL_TO_DATE"
    BETWEEN_DATES = "BETWEEN_DATES"
    OUTSIDE_OF_DATES = "OUTSIDE_OF_DATES"


class TimeRangeConditionType(str, Enum):
    GREATER_THAN_TIME_RANGE = "GREATER_THAN_TIME_RANGE"
    LESS_THAN_TIMES_RANGE = "LESS_THAN_TIME_RANGE"
    BETWEEN_TIMES_RANGE = "BETWEEN_TIMES_RANGE"
    EQUAL_TO_TIMES_RANGE = "EQUAL_TO_TIME_RANGE"
    NOT_EQUAL_TO_TIMES_RANGE = "NOT_EQUAL_TO_TIME_RANGE"
    OUTSIDE_OF_TIMES_RANGE = "OUTSIDE_OF_TIMES_RANGE"


class TimeConditionType(str, Enum):
    GREATER_THAN_TIME = "GREATER_THAN_TIME"
    LESS_THAN_TIME = "LESS_THAN_TIME"
    BETWEEN_TIMES = "BETWEEN_TIMES"
    EQUAL_TO_TIME = "EQUAL_TO_TIME"
    NOT_EQUAL_TO_TIMES = "NOT_EQUAL_TO_TIME"
    OUTSIDE_OF_TIMES = "OUTSIDE_OF_TIMES"


class MultiSelectConditionType(str, Enum):
    INCLUDES_OPTION = "INCLUDES_OPTION"
    NOT_INCLUDES_OPTION = "NOT_INCLUDES_OPTION"


class MultiSelectionsPerRowConditionType(str, Enum):
    INCLUDES_ROW_OPTION = "INCLUDES_ROW_OPTION"
    NOT_INCLUDES_ROW_OPTION = "NOT_INCLUDES_ROW_OPTION"


class SingleSelectionPerRowConditionType(str, Enum):
    EQUAL_TO_ROW_OPTION = "EQUAL_TO_ROW_OPTION"
    NOT_EQUAL_TO_ROW_OPTION = "NOT_EQUAL_TO_ROW_OPTION"


class SingleSelectConditionType(str, Enum):
    EQUAL_TO_OPTION = "EQUAL_TO_OPTION"
    NOT_EQUAL_TO_OPTION = "NOT_EQUAL_TO_OPTION"


class SliderRowConditionType(str, Enum):
    GREATER_THAN_SLIDER_ROWS = "GREATER_THAN_SLIDER_ROWS"
    LESS_THAN_SLIDER_ROWS = "LESS_THAN_SLIDER_ROWS"
    EQUAL_TO_SLIDER_ROWS = "EQUAL_TO_SLIDER_ROWS"
    NOT_EQUAL_TO_SLIDER_ROWS = "NOT_EQUAL_TO_SLIDER_ROWS"
    BETWEEN_SLIDER_ROWS = "BETWEEN_SLIDER_ROWS"
    OUTSIDE_OF_SLIDER_ROWS = "OUTSIDE_OF_SLIDER_ROWS"


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
    SingleSelectionPerRowConditionType.EQUAL_TO_ROW_OPTION,
    SingleSelectionPerRowConditionType.NOT_EQUAL_TO_ROW_OPTION,
    MultiSelectionsPerRowConditionType.INCLUDES_ROW_OPTION,
    MultiSelectionsPerRowConditionType.NOT_INCLUDES_ROW_OPTION,
]


class OptionPayload(PublicModelNoExtra):
    option_value: str


class OptionIndexPayload(OptionPayload):
    row_index: str


class ValuePayload(PublicModelNoExtra):
    value: float

    @validator("value")
    def validate_score(cls, value):
        return round(value, 2)


class ValueIndexPayload(ValuePayload):
    row_index: str


class SingleDatePayload(PublicModel):
    date: datetime.date

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d["date"] = self.date.isoformat()
        return d


class DateRangePayload(PublicModel):
    minDate: datetime.date
    maxDate: datetime.date

    @root_validator(pre=True)
    def validate_dates(cls, values):
        min_date = values.get("minDate")
        max_date = values.get("maxDate")
        if min_date and max_date and min_date > max_date:
            raise ValueError("minDate cannot be later than maxDate")
        return values

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d["minDate"] = self.minDate.isoformat()
        d["maxDate"] = self.maxDate.isoformat()
        return d


class TimePayload(PublicModel):
    type: str | None = None
    value: datetime.time

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d["value"] = self.value.strftime("%H:%M")
        return d


class SingleTimePayload(PublicModel):
    time: Optional[datetime.time] = None

    @root_validator(pre=True)
    def validate_time(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        time_value = values.get("time")
        if isinstance(time_value, dict):
            values["time"] = cls._dict_to_time(time_value)
        elif isinstance(time_value, str):
            values["time"] = cls._string_to_time(time_value)
        return values

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        d = super().dict(*args, **kwargs)
        if self.time:
            d["time"] = self.time.strftime("%H:%M")
        return d

    @staticmethod
    def _dict_to_time(time_dict: Dict[str, Any]) -> datetime.time:
        if "hours" in time_dict and "minutes" in time_dict:
            return datetime.time(hour=int(time_dict["hours"]), minute=int(time_dict["minutes"]))
        raise ValueError("Invalid time dictionary structure")

    @staticmethod
    def _string_to_time(time_string: str) -> datetime.time:
        try:
            return datetime.datetime.strptime(time_string, "%H:%M").time()
        except ValueError:
            raise ValueError("Invalid time string format. Expected 'HH:MM'.")

    @staticmethod
    def _time_to_dict(time: datetime.time) -> Dict[str, int]:
        return {"hours": time.hour, "minutes": time.minute}


class MinMaxTimePayload(PublicModel):
    minTime: Optional[datetime.time] = None
    maxTime: Optional[datetime.time] = None

    @root_validator(pre=True)
    def validate_times(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        min_time_dict = values.get("minTime")
        max_time_dict = values.get("maxTime")

        if isinstance(min_time_dict, dict):
            values["minTime"] = cls._dict_to_time(min_time_dict)
        if isinstance(max_time_dict, dict):
            values["maxTime"] = cls._dict_to_time(max_time_dict)

        return values

    def dict(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        d = super().dict(*args, **kwargs)
        if self.minTime:
            d["minTime"] = self._time_to_dict(self.minTime)
        if self.maxTime:
            d["maxTime"] = self._time_to_dict(self.maxTime)
        return {key: value for key, value in d.items() if value is not None}

    @staticmethod
    def _dict_to_time(time_dict: Dict[str, int]) -> datetime.time:
        if "hours" in time_dict and "minutes" in time_dict:
            return datetime.time(hour=int(time_dict["hours"]), minute=int(time_dict["minutes"]))
        raise ValueError("Invalid time dictionary structure")

    @staticmethod
    def _time_to_dict(time: datetime.time) -> Dict[str, int]:
        return {"hours": time.hour, "minutes": time.minute}

    def json_serialize(self) -> Dict[str, Any]:
        data = self.dict()
        if self.minTime:
            data["minTime"] = self._time_to_dict(self.minTime)
        if self.maxTime:
            data["maxTime"] = self._time_to_dict(self.maxTime)
        return data


class MinMaxSliderRowPayload(PublicModelNoExtra):
    minValue: float
    maxValue: float
    rowIndex: str

    @validator("minValue", "maxValue")
    def validate_score(cls, value):
        return round(value, 2)

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d["minValue"] = round(self.minValue, 2)
        d["maxValue"] = round(self.maxValue, 2)
        return d


class MinMaxPayload(PublicModelNoExtra):
    min_value: float
    max_value: float

    @validator("min_value", "max_value")
    def validate_score(cls, value):
        return round(value, 2)


class MinMaxPayloadRow(MinMaxPayload):
    row_index: str


class ScoreConditionPayload(PublicModel):
    value: bool


class BaseCondition(PublicModel):
    item_name: str


class _IncludesOptionCondition(BaseCondition):
    type: str = Field(ConditionType.INCLUDES_OPTION, const=True)


class _IncludesOptionPerRowCondition(BaseCondition):
    type: str = Field(MultiSelectionsPerRowConditionType.INCLUDES_ROW_OPTION, const=True)


class _NotIncludesOptionPerRowCondition(BaseCondition):
    type: str = Field(MultiSelectionsPerRowConditionType.NOT_INCLUDES_ROW_OPTION, const=True)


class _NotIncludesOptionCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_INCLUDES_OPTION, const=True)


class _EqualToOptionCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL_TO_OPTION, const=True)


class _EqualToRowOptionCondition(BaseCondition):
    type: str = Field(SingleSelectionPerRowConditionType.EQUAL_TO_ROW_OPTION, const=True)


class _NotEqualToRowOptionCondition(BaseCondition):
    type: str = Field(SingleSelectionPerRowConditionType.NOT_EQUAL_TO_ROW_OPTION, const=True)


class _NotEqualToOptionCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_EQUAL_TO_OPTION, const=True)


class _GraterThanDateCondition(BaseCondition):
    type: str = Field(DateConditionType.GREATER_THAN_DATE, const=True)


class _LessThanDateCondition(BaseCondition):
    type: str = Field(DateConditionType.LESS_THAN_DATE, const=True)


class _GreaterThanSliderRowCondition(BaseCondition):
    type: str = Field(SliderRowConditionType.GREATER_THAN_SLIDER_ROWS, const=True)


class _LessThanSliderRowCondition(BaseCondition):
    type: str = Field(SliderRowConditionType.LESS_THAN_SLIDER_ROWS, const=True)


class _EqualToSliderRowCondition(BaseCondition):
    type: str = Field(SliderRowConditionType.EQUAL_TO_SLIDER_ROWS, const=True)


class _NotEqualToSliderRowCondition(BaseCondition):
    type: str = Field(SliderRowConditionType.NOT_EQUAL_TO_SLIDER_ROWS, const=True)


class _BetweenSliderRowCondition(BaseCondition):
    type: str = Field(SliderRowConditionType.BETWEEN_SLIDER_ROWS, const=True)


class _OutsideOfSliderRowCondition(BaseCondition):
    type: str = Field(SliderRowConditionType.OUTSIDE_OF_SLIDER_ROWS, const=True)


class _BetweenTimeRangeCondition(BaseCondition):
    type: str = Field(TimeRangeConditionType.BETWEEN_TIMES_RANGE, const=True)


class _GreaterThanTimeRangeCondition(BaseCondition):
    type: str = Field(TimeRangeConditionType.GREATER_THAN_TIME_RANGE, const=True)


class _EqualToTimeRangeCondition(BaseCondition):
    type: str = Field(TimeRangeConditionType.EQUAL_TO_TIMES_RANGE, const=True)


class _EqualToTimeCondition(BaseCondition):
    type: str = Field(TimeConditionType.EQUAL_TO_TIME, const=True)


class _NotEqualToTimeCondition(BaseCondition):
    type: str = Field(TimeConditionType.NOT_EQUAL_TO_TIMES, const=True)


class _LessThanTimeRangeCondition(BaseCondition):
    type: str = Field(TimeRangeConditionType.LESS_THAN_TIMES_RANGE, const=True)


class _LessThanTimeCondition(BaseCondition):
    type: str = Field(TimeConditionType.LESS_THAN_TIME, const=True)


class _BetweenTimeCondition(BaseCondition):
    type: str = Field(TimeConditionType.BETWEEN_TIMES, const=True)


class _NotEqualToTimeRangeCondition(BaseCondition):
    type: str = Field(TimeRangeConditionType.NOT_EQUAL_TO_TIMES_RANGE, const=True)


class _OutsideOfTimeRangeCondition(BaseCondition):
    type: str = Field(TimeRangeConditionType.OUTSIDE_OF_TIMES_RANGE, const=True)


class _GreaterThanTimeCondition(BaseCondition):
    type: str = Field(TimeConditionType.GREATER_THAN_TIME, const=True)


class _OutsideOfTimeCondition(BaseCondition):
    type: str = Field(TimeConditionType.OUTSIDE_OF_TIMES, const=True)


class _GreaterThanCondition(BaseCondition):
    type: str = Field(ConditionType.GREATER_THAN, const=True)


class _LessThanCondition(BaseCondition):
    type: str = Field(ConditionType.LESS_THAN, const=True)


class _EqualCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL, const=True)


class _EqualToDateCondition(BaseCondition):
    type: str = Field(DateConditionType.EQUAL_TO_DATE, const=True)


class _NotEqualToDateCondition(BaseCondition):
    type: str = Field(DateConditionType.NOT_EQUAL_TO_DATE, const=True)


class _NotEqualCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_EQUAL, const=True)


class _BetweenCondition(BaseCondition):
    type: str = Field(ConditionType.BETWEEN, const=True)


class _BetweenDatesCondition(BaseCondition):
    type: str = Field(DateConditionType.BETWEEN_DATES, const=True)


class _OutsideOfDatesCondition(BaseCondition):
    type: str = Field(DateConditionType.OUTSIDE_OF_DATES, const=True)


class _OutsideOfCondition(BaseCondition):
    type: str = Field(ConditionType.OUTSIDE_OF, const=True)


class IncludesOptionCondition(_IncludesOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class IncludesOptionPerRowCondition(_IncludesOptionPerRowCondition):
    payload: OptionPayload | OptionIndexPayload


class NotIncludesOptionPerRowCondition(_NotIncludesOptionPerRowCondition):
    payload: OptionPayload | OptionIndexPayload


class NotIncludesOptionCondition(_NotIncludesOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class EqualToOptionCondition(_EqualToOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class EqualToRowOptionCondition(_EqualToRowOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class NotEqualToRowOptionCondition(_NotEqualToRowOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class NotEqualToOptionCondition(_NotEqualToOptionCondition):
    payload: OptionPayload | OptionIndexPayload


class GreaterThanDateCondition(_GraterThanDateCondition):
    payload: SingleDatePayload


class GreaterThanSliderRowCondition(_GreaterThanSliderRowCondition):
    payload: ValuePayload | ValueIndexPayload


class LessThanSliderRowCondition(_LessThanSliderRowCondition):
    payload: ValuePayload | ValueIndexPayload


class EqualToSliderRowCondition(_EqualToSliderRowCondition):
    payload: ValuePayload | ValueIndexPayload


class NotEqualToSliderRowCondition(_NotEqualToSliderRowCondition):
    payload: ValuePayload | ValueIndexPayload


class BetweenSliderRowCondition(_BetweenSliderRowCondition):
    payload: MinMaxSliderRowPayload | ValueIndexPayload


class OutsideOfSliderRowCondition(_OutsideOfSliderRowCondition):
    payload: MinMaxSliderRowPayload | ValueIndexPayload


class LessThanDateCondition(_LessThanDateCondition):
    payload: SingleDatePayload


class BetweenTimeRangeCondition(_BetweenTimeRangeCondition):
    payload: MinMaxTimePayload


class GreaterThanTimeRangeCondition(_GreaterThanTimeRangeCondition):
    payload: SingleTimePayload


class LessThanTimeRangeCondition(_LessThanTimeRangeCondition):
    payload: SingleTimePayload


class EqualToTimeRangeCondition(_EqualToTimeRangeCondition):
    payload: SingleTimePayload


class NotEqualToTimeRangeCondition(_NotEqualToTimeRangeCondition):
    payload: SingleTimePayload


class OutsideOfTimeRangeCondition(_OutsideOfTimeRangeCondition):
    payload: MinMaxTimePayload


class GreaterThanTimeCondition(_GreaterThanTimeCondition):
    payload: SingleTimePayload


class LessThanTimeCondition(_LessThanTimeCondition):
    payload: SingleTimePayload


class EqualToTimeCondition(_EqualToTimeCondition):
    payload: SingleTimePayload


class NotEqualToTimeCondition(_NotEqualToTimeCondition):
    payload: SingleTimePayload


class OutsideOfTimeCondition(_OutsideOfTimeCondition):
    payload: MinMaxTimePayload


class BetweenTimeCondition(_BetweenTimeCondition):
    payload: MinMaxTimePayload


class GreaterThanCondition(_GreaterThanCondition):
    payload: ValuePayload | TimePayload


class LessThanCondition(_LessThanCondition):
    payload: ValuePayload | ValueIndexPayload | TimePayload


class EqualToDateCondition(_EqualToDateCondition):
    payload: SingleDatePayload


class EqualCondition(_EqualCondition):
    payload: ValuePayload | ValueIndexPayload | TimePayload


class NotEqualToDateCondition(_NotEqualToDateCondition):
    payload: SingleDatePayload


class NotEqualCondition(_NotEqualCondition):
    payload: ValuePayload | ValueIndexPayload | TimePayload


class BetweenDatesCondition(_BetweenDatesCondition):
    payload: DateRangePayload


class BetweenCondition(_BetweenCondition):
    payload: MinMaxPayload | MinMaxPayloadRow | TimePayload


class OutsideOfCondition(_OutsideOfCondition):
    payload: MinMaxPayload | MinMaxPayloadRow | TimePayload


class OutsideOfDatesCondition(_OutsideOfDatesCondition):
    payload: DateRangePayload


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
    | GreaterThanDateCondition
    | BetweenTimeRangeCondition
    | LessThanDateCondition
    | EqualToDateCondition
    | BetweenDatesCondition
    | NotEqualToDateCondition
    | OutsideOfDatesCondition
    | GreaterThanTimeRangeCondition
    | LessThanTimeRangeCondition
    | EqualToTimeRangeCondition
    | NotEqualToTimeRangeCondition
    | OutsideOfTimeRangeCondition
    | EqualToRowOptionCondition
    | NotEqualToRowOptionCondition
    | IncludesOptionPerRowCondition
    | NotIncludesOptionPerRowCondition
    | GreaterThanSliderRowCondition
    | LessThanSliderRowCondition
    | EqualToSliderRowCondition
    | NotEqualToSliderRowCondition
    | BetweenSliderRowCondition
    | OutsideOfSliderRowCondition
    | GreaterThanTimeCondition
    | LessThanTimeCondition
    | EqualToTimeCondition
    | NotEqualToTimeCondition
    | BetweenTimeCondition
    | OutsideOfTimeCondition
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
