from pydantic import BaseModel


class SuperAdmin(BaseModel):
    email: str = "admin@gettingcurious.com"
    password: str = "superAdminPassword!"
    first_name: str = "Mindlogger"
    last_name: str = "ChildMindInstitute"
