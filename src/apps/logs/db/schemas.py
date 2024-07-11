from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB

from infrastructure.database.base import Base


class NotificationLogSchema(Base):
    __tablename__ = "notification_logs"

    user_id = Column(String(), nullable=False)
    device_id = Column(String(), nullable=False)
    action_type = Column(String(), nullable=False)
    notification_descriptions = Column(JSONB(), nullable=True)
    notification_in_queue = Column(JSONB(), nullable=True)
    scheduled_notifications = Column(JSONB(), nullable=True)
    notification_descriptions_updated = Column(Boolean(), nullable=False)
    notifications_in_queue_updated = Column(Boolean(), nullable=False)
    scheduled_notifications_updated = Column(Boolean(), nullable=False)


class UserActivityLogSchema(Base):
    __tablename__ = "user_activity_logs"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    firebase_token_id = Column(String(), nullable=True)
    event_type = Column(String(), nullable=False)
    event = Column(String(), nullable=False)
    user_agent = Column(String(), nullable=True)
    mindlogger_content = Column(String(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"UserActivityLogSchema(id='{self.id}', user_id='{self.user_id}',"
            f" event_type='{self.event_type}', event='{self.event}')"
        )
