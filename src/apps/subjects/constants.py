from enum import Enum


class SubjectStatus(str, Enum):
    INVITED = "invited"
    NOT_INVITED = "not_invited"
    PENDING = "pending"
