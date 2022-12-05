from sqlalchemy import Column, ForeignKey, String, Enum

from apps.users.db.constants import Role
from infrastructure.database.base import Base


# Properties to receive via API on creation
class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=100), unique=True)
    full_name = Column(String(length=100))
    hashed_password = Column(String(length=100))


class UserAppletAccessSchema(Base):
    __tablename__ = "user_applet_accesses"

    user_id = Column(ForeignKey("users.id"), primary_key=True)
    applet_id = Column(ForeignKey("applets.id"), primary_key=True)
    role = Column(Enum(Role), primary_key=True)
