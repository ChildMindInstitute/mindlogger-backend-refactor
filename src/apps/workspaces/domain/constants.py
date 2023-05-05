from enum import Enum
from functools import lru_cache


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    OWNER = "owner"
    MANAGER = "manager"
    COORDINATOR = "coordinator"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    RESPONDENT = "respondent"

    @classmethod
    @lru_cache
    def as_list(cls) -> list[str]:
        return [role for role in cls]

    def __lt__(self, other):
        roles = self.as_list()
        return roles.index(self) > roles.index(other)


class ManagersRole(str, Enum):
    MANAGER = "manager"
    COORDINATOR = "coordinator"
    EDITOR = "editor"


class DataRetention(str, Enum):
    INDEFINITELY = "indefinitely"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"
