from sqlalchemy import Boolean, Column, String, JSON

from infrastructure.database.base import Base


class NotificationLogSchema(Base):
    __tablename__ = "notification_logs"

    user_id = Column(String, nullable=False)
    device_id = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    notification_descriptions = Column(String, nullable=True)
    notification_in_queue = Column(String, nullable=True)
    scheduled_notifications = Column(String, nullable=True)
    notification_descriptions_updated = Column(Boolean, nullable=True)
    notifications_in_queue_updated = Column(Boolean, nullable=True)
    scheduled_notifications_updated = Column(Boolean, nullable=True)
