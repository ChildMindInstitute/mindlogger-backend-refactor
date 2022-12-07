from sqlalchemy import Column, ForeignKey, String

from infrastructure.database.base import Base


class AppletSchema(Base):
    __tablename__ = "applets"

    display_name = Column(String(length=100), unique=True)
    description = Column(String(length=100))


class UserAppletAccessSchema(Base):
    __tablename__ = "user_applet_accesses"

    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    applet_id = Column(
        ForeignKey("applets.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(length=20), nullable=False)
