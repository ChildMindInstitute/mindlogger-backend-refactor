from sqlalchemy import Column, String

from infrastructure.database.base import Base


# Properties to receive via API on creation
class TokenSchema(Base):
    __tablename__ = "tokens"

    email = Column(String(length=100))
    access_token = Column(String(length=256))
    refresh_token = Column(String(length=256))
