from sqlalchemy import Column, String

from infrastructure.database.base import Base


# Properties to receive via API on creation
class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=100), unique=True)
    full_name = Column(String(length=100))
    hashed_password = Column(String(length=100))
