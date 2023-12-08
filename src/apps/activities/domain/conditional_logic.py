from enum import Enum

from pydantic import Field

from apps.activities.domain.conditions import Condition
from apps.shared.domain import PublicModel


class Match(str, Enum):
    ANY = "any"
    ALL = "all"


class ConditionalLogic(PublicModel):
    match: Match = Field(default=Match.ALL)
    conditions: list[Condition]
