from enum import Enum


class SubjectStatus(str, Enum):
    INVITED = "invited"
    NOT_INVITED = "not_invited"
    PENDING = "pending"


class Relation(str, Enum):
    # todo: TBD with team list of relation types
    pass
