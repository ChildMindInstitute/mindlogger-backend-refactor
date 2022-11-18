from sqlalchemy import Column, String

from apps.shared.domain import Model
from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    username = Column(String(length=100))
    email = Column(String(length=100))


class UserCreateSchema(Model):
    username: str
    email: str
