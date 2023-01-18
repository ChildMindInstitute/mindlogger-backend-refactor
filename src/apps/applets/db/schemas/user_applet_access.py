from sqlalchemy import Column, ForeignKey, String

from infrastructure.database.base import Base


class UserAppletAccessSchema(Base):
    __tablename__ = "user_applet_accesses"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )
    role = Column(String(length=20), nullable=False)
