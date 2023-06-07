from pydantic import BaseModel


class AnonymousRespondent(BaseModel):
    email: str = "anonymous_respondent@mindlogger.com"
    password: str = "anonymousRespondentPassword!"
    first_name: str = "Mindlogger"
    last_name: str = "ChildMindInstitute"
    force_update: bool = False
