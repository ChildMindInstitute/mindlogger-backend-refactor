from pydantic import EmailStr

from apps.shared.domain import Model


# Properties to receive via API on creation
class UserCreate(Model):
    email: EmailStr
    password: str
    fullname: str
