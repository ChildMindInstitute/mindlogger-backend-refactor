from pydantic import BaseModel


class ProlificRespondent(BaseModel):
    domain: str = "prolific.com"
    password: str = "prolificRespondentPassword!"
    first_name: str = "Prolific"
    last_name: str = "ChildMindInstitute"
    secret_user_id: str = "ProlificRespondent: "
