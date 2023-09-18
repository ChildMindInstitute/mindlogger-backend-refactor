from pydantic import BaseModel


class LegacyDeletedRespondent(BaseModel):
    email: str = "legacy_deleted_respondent@mindlogger.com"
    password: str = "legacyDeletedRespondentPassword!"
    first_name: str = "Legacy Deleted"
    last_name: str = "ChildMindInstitute"
    force_update: bool = False
