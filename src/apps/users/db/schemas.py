from pydantic import EmailStr
from sqlalchemy import Boolean, Column, String

from apps.shared.domain import Model
from infrastructure.database.base import Base


# Shared properties
class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=100))
    username = Column(String(length=100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)


# Properties to receive via API on creation
class UserCreate(Model):
    email: EmailStr
    password: str
    username: str
