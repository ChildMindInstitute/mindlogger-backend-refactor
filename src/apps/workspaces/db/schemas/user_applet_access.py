from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB

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
    owner_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    invitor_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    meta = Column(JSONB())
    is_pinned = Column(Boolean(), default=False)
