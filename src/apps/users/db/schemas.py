from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Unicode
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from apps.shared.enums import ColumnCommentType
from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=56), unique=True)
    email_encrypted = Column(StringEncryptedType(Unicode, get_key), default=None, comment=ColumnCommentType.ENCRYPTED)
    first_name = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    last_name = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    hashed_password = Column(String(length=100))
    last_seen_at = Column(DateTime(), default=datetime.utcnow)
    is_super_admin = Column(Boolean(), default=False, server_default="false")
    is_anonymous_respondent = Column(Boolean(), default=False, server_default="false")
    is_legacy_deleted_respondent = Column(Boolean(), default=False, server_default="false")

    def __repr__(self) -> str:
        return f"UserSchema(id='{self.id}', email='{self.email}')"  # pragma: no cover # noqa: E501

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}" if self.last_name else self.first_name


class UserDeviceSchema(Base):
    __tablename__ = "user_devices"

    user_id = Column(ForeignKey("users.id"))
    device_id = Column(String(255))
