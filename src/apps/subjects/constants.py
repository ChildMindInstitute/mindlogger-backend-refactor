from enum import StrEnum


class SubjectStatus(StrEnum):
    INVITED = "invited"
    NOT_INVITED = "not_invited"
    PENDING = "pending"


class Relation(StrEnum):
    self = "self"
    admin = "admin"
    other = "other"


class SubjectTag(StrEnum):
    TEAM = "Team"
    # Todo: Add more tags
