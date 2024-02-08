from pydantic import BaseModel


class SuperAdmin(BaseModel):
    email: str = "admin@mindlogger.com"
    password: str = "superAdminPassword!"
    first_name: str = "Mindlogger"
    last_name: str = "ChildMindInstitute"
