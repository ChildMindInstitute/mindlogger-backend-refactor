from sqlalchemy import Column, ForeignKey, String

from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    email = Column(String(length=100), unique=True)
    full_name = Column(String(length=100))
    hashed_password = Column(String(length=100))


class UserAppletAccessSchema(Base):
    __tablename__ = "user_applet_accesses"

    user_id = Column(ForeignKey("users.id"), nullable=False)
    applet_id = Column(ForeignKey("applets.id"), nullable=False)
    role = Column(String(length=20), nullable=False)
