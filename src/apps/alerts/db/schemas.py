from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database.base import Base


class AlertSchema(Base):
    """This table is used as responses to specific flow activity items"""

    __tablename__ = "alerts"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    is_watched = Column(Boolean(), nullable=False, default=False)
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version = Column(String())
    activity_id = Column(UUID(as_uuid=True))
    activity_item_id = Column(UUID(as_uuid=True))
    alert_message = Column(String(), nullable=False)
    answer_id = Column(UUID(as_uuid=True))
