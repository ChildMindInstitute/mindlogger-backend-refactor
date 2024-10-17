from enum import StrEnum
from functools import lru_cache


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    OWNER = "owner"
    MANAGER = "manager"
    COORDINATOR = "coordinator"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    RESPONDENT = "respondent"

    @classmethod
    @lru_cache
    def as_list(cls) -> list["Role"]:
        return [cls(role) for role in cls]

    def __lt__(self, other):
        roles = self.as_list()
        return roles.index(self) > roles.index(other)

    @classmethod
    def editors(cls) -> list["Role"]:
        return [cls.OWNER, cls.MANAGER, cls.EDITOR]

    @classmethod
    def super_inviters(cls) -> list["Role"]:
        return [cls.OWNER, cls.MANAGER]

    @classmethod
    def inviters(cls) -> list["Role"]:
        return [cls.OWNER, cls.MANAGER, cls.COORDINATOR]

    @classmethod
    def schedulers(cls) -> list["Role"]:
        return [cls.OWNER, cls.MANAGER, cls.COORDINATOR]

    @classmethod
    def managers(cls) -> list["Role"]:
        return [
            cls.OWNER,
            cls.MANAGER,
            cls.COORDINATOR,
            cls.EDITOR,
            cls.REVIEWER,
        ]

    @classmethod
    def super_reviewers(cls) -> list["Role"]:
        return [cls.OWNER, cls.MANAGER]

    @classmethod
    def reviewers(cls) -> list["Role"]:
        return [cls.OWNER, cls.MANAGER, cls.REVIEWER]


class ManagersRole(StrEnum):
    MANAGER = "manager"
    COORDINATOR = "coordinator"
    EDITOR = "editor"


class UserPinRole(StrEnum):
    manager = "manager"
    respondent = "respondent"


class DataRetention(StrEnum):
    INDEFINITELY = "indefinitely"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"
