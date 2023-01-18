from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import JSONB

from infrastructure.database.base import Base


class NotificationLogSchema(Base):
    __tablename__ = "notification_logs"

    user_id = Column(String, nullable=False)
    device_id = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    notification_descriptions = Column(JSONB, nullable=True)
    notification_in_queue = Column(JSONB, nullable=True)
    scheduled_notifications = Column(JSONB, nullable=True)
    notification_descriptions_updated = Column(Boolean, nullable=False)
    notifications_in_queue_updated = Column(Boolean, nullable=False)
    scheduled_notifications_updated = Column(Boolean, nullable=False)
