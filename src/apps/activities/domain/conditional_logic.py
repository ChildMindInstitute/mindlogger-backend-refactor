from enum import Enum
from pydantic import BaseModel, Field, root_validator, validator

from apps.shared.domain import PublicModel
from apps.activities.domain.conditions import Condition, ConditionType


class Match(str, Enum):
    ANY = "any"
    ALL = "all"


class ConditionalLogic(PublicModel):
    match: Match = Field(default=Match.ALL)
    conditions: list[Condition]
