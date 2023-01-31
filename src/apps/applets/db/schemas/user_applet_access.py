from sqlalchemy import Column, ForeignKey, String

from infrastructure.database.base import Base

__all__ = ["UserAppletAccessSchema"]


class UserAppletAccessSchema(Base):
    __tablename__ = "user_applet_accesses"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role = Column(String(length=20), nullable=False, index=True)
