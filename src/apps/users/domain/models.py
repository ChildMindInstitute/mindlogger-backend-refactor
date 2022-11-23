from sqlalchemy import Boolean, Column, String
from pydantic import BaseModel, Field, EmailStr
from pydantic.types import PositiveInt

from apps.shared.domain import BaseError
from apps.users.db.schemas import UserCreate
from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=100))
    fullname = Column(String(length=100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    password = Column(String(length=100))

    class Config:
        schema_extra = {
            "example": {
                "email": "example@gmail.com",
                "fullname": "Example Fullname",
                "is_active": "True",
                "is_superuser": "False",
                "password": "examplepassword",
                "created_at": "",
                "updated_at": "",
                "is_deleted": "False"
            }
        }


class UserLoginSchema(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "email": "example@gmail.com",
                "password": "examplepassword"
            }
        }


class UsersError(BaseError):
    def __init__(self, message: str | None = None, *args, **kwargs) -> None:
        message = (
            message
            or "Can not find your user in the database. Please register first."
        )
        super().__init__(message, *args, **kwargs)


class User(UserCreate):
    id: PositiveInt

    def __str__(self) -> str:
        return self.email
