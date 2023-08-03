from enum import Enum

from pydantic import Field

from apps.shared.domain import PublicModel


class ConditionType(str, Enum):
    INCLUDES_OPTION = "includesOption"
    NOT_INCLUDES_OPTION = "notIncludesOption"
    EQUAL_TO_OPTION = "equalToOption"
    NOT_EQUAL_TO_OPTION = "notEqualToOption"
    GREATER_THAN = "greaterThan"
    LESS_THAN = "lessThan"
    EQUAL = "equal"
    NOT_EQUAL = "notEqual"
    BETWEEN = "between"
    OUTSIDE_OF = "outsideOf"
    EQUAL_TO_SCORE = "equalToScore"


class MultiSelectConditionType(str, Enum):
    INCLUDES_OPTION = "includesOption"
    NOT_INCLUDES_OPTION = "notIncludesOption"


class SingleSelectConditionType(str, Enum):
    EQUAL_TO_OPTION = "equalToOption"
    NOT_EQUAL_TO_OPTION = "notEqualToOption"


class SliderConditionType(str, Enum):
    GREATER_THAN = "greaterThan"
    LESS_THAN = "lessThan"
    EQUAL = "equal"
    NOT_EQUAL = "notEqual"
    BETWEEN = "between"
    OUTSIDE_OF = "outsideOf"


class OptionPayload(PublicModel):
    option_value: str


class ValuePayload(PublicModel):
    value: int


class MinMaxPayload(PublicModel):
    min_value: int
    max_value: int


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
    payload: ValuePayload


class LessThanCondition(BaseCondition):
    type: str = Field(ConditionType.LESS_THAN, const=True)
    payload: ValuePayload


class EqualCondition(BaseCondition):
    type: str = Field(ConditionType.EQUAL, const=True)
    payload: ValuePayload


class NotEqualCondition(BaseCondition):
    type: str = Field(ConditionType.NOT_EQUAL, const=True)
    payload: ValuePayload


class BetweenCondition(BaseCondition):
    type: str = Field(ConditionType.BETWEEN, const=True)
    payload: MinMaxPayload


class OutsideOfCondition(BaseCondition):
    type: str = Field(ConditionType.OUTSIDE_OF, const=True)
    payload: MinMaxPayload


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
