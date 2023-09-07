from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
)

from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=56), unique=True)
    email_aes_encrypted = Column(LargeBinary(length=100), default=None)
    email_encrypted = Column(Text(), default=None)
    first_name = Column(Text())
    last_name = Column(Text())
    hashed_password = Column(String(length=100))
    last_seen_at = Column(DateTime(), default=datetime.utcnow)
    is_super_admin = Column(Boolean(), default=False, server_default="false")
    is_anonymous_respondent = Column(
        Boolean(), default=False, server_default="false"
    )
    is_legacy_deleted_respondent = Column(
        Boolean(), default=False, server_default="false"
    )

    def __repr__(self):
        return f"UserSchema(id='{self.id}', email='{self.email}')"


class UserDeviceSchema(Base):
    __tablename__ = "user_devices"

    user_id = Column(ForeignKey("users.id"))
    device_id = Column(String(255))
