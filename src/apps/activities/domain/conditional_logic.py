from enum import StrEnum

from pydantic import Field

from apps.activities.domain.conditions import Condition
from apps.shared.domain import PublicModel


class Match(StrEnum):
    ANY = "any"
    ALL = "all"


class ConditionalLogic(PublicModel):
    match: Match = Field(default=Match.ALL)
    conditions: list[Condition]
