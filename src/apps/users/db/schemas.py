from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Unicode, UniqueConstraint
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=56), unique=True)
    email_encrypted = Column(StringEncryptedType(Unicode, get_key), default=None)
    first_name = Column(StringEncryptedType(Unicode, get_key))
    last_name = Column(StringEncryptedType(Unicode, get_key))
    hashed_password = Column(String(length=100))
    last_seen_at = Column(DateTime(), default=datetime.utcnow)
    is_super_admin = Column(Boolean(), default=False, server_default="false")
    is_anonymous_respondent = Column(Boolean(), default=False, server_default="false")
    is_legacy_deleted_respondent = Column(Boolean(), default=False, server_default="false")
    is_prolific_respondent = Column(Boolean(), default=False, server_default="false")

    def __repr__(self) -> str:
        return f"UserSchema(id='{self.id}', email='{self.email}')"  # pragma: no cover # noqa: E501

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}" if self.last_name else self.first_name


class UserDeviceSchema(Base):
    __tablename__ = "user_devices"

    uq_constraint = "uq_user_devices_user_device"

    __table_args__ = (UniqueConstraint("user_id", "device_id", name=uq_constraint),)

    user_id = Column(ForeignKey("users.id"))
    device_id = Column(String(255))
    os_name = Column(Text, nullable=True)
    os_version = Column(Text, nullable=True)
    app_version = Column(Text, nullable=True)
