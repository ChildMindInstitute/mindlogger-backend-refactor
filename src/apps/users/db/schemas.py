from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Unicode
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=56), unique=True)
    email_encrypted = Column(
        StringEncryptedType(Unicode, get_key), default=None
    )
    first_name = Column(StringEncryptedType(Unicode, get_key))
    last_name = Column(StringEncryptedType(Unicode, get_key))
    hashed_password = Column(String(length=100))
    last_seen_at = Column(DateTime(), default=datetime.utcnow)
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
