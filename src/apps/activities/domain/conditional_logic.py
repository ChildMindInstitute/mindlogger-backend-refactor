from enum import StrEnum

from apps.activities.domain.conditions import Condition
from apps.shared.domain import PublicModel


class Match(StrEnum):
    ANY = "any"
    ALL = "all"


class ConditionalLogic(PublicModel):
    match: Match = Match.ALL
    conditions: list[Condition]
