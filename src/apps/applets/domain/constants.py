from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    COORDINATOR = "coordinator"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    RESPONDENT = "respondent"


class RoleLevel(int, Enum):
    ADMIN = 1  # the highest
    MANAGER = 2
    COORDINATOR = 3
    EDITOR = 4
    REVIEWER = 5
    RESPONDENT = 6  # the lowest

    @classmethod
    def by_role(cls, role: Role):
        """
        returns level by role, if not found return the lowest role
        """
        return cls._member_map_.get(role.name, 1000)
