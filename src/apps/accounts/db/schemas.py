from sqlalchemy import Column, String

from infrastructure.database.base import Base


class AccountSchema(Base):
    __tablename__ = "accounts"

    user_id = Column(String(length=100))
    account_name = Column(String(length=100))
