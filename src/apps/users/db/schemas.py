from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
)

from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=56), unique=True)
    email_aes_encrypted = Column(LargeBinary(length=100), default=None)
    first_name = Column(LargeBinary(length=100), default=None)
    last_name = Column(LargeBinary(length=100), default=None)
    hashed_password = Column(String(length=100))
    last_seen_at = Column(DateTime(), default=datetime.now)
    is_super_admin = Column(Boolean(), default=False, server_default="false")
    is_anonymous_respondent = Column(
        Boolean(), default=False, server_default="false"
    )

    def __repr__(self):
        return f"UserSchema(id='{self.id}', email='{self.email}')"


class UserDeviceSchema(Base):
    __tablename__ = "user_devices"

    user_id = Column(ForeignKey("users.id"))
    device_id = Column(String(255))
