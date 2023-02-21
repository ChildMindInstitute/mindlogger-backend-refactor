from sqlalchemy import Column, String

from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=100), unique=True)
    first_name = Column(String(length=50))
    last_name = Column(String(length=50))
    hashed_password = Column(String(length=100))
