from sqlalchemy import Boolean, Column, ForeignKey, String, Unicode
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
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
    subject_id = Column(
        ForeignKey("subjects.id", ondelete="RESTRICT"),
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
    alert_message = Column(StringEncryptedType(Unicode, get_key), nullable=False)
    answer_id = Column(UUID(as_uuid=True))
    type = Column(String())
