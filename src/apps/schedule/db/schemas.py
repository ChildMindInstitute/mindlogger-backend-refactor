import datetime

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, Interval, String, Time, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ENUM, UUID

from infrastructure.database.base import Base
from infrastructure.database.mixins import HistoryAware


class _BaseEventSchema:
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    access_before_schedule = Column(Boolean, nullable=True)
    one_time_completion = Column(Boolean, nullable=True)
    timer = Column(Interval, nullable=True)
    timer_type = Column(String(10), nullable=False)  # NOT_SET, TIMER, IDLE
    version = Column(
        String(13),
        nullable=True,
        default=lambda: datetime.datetime.now(datetime.UTC).strftime("%Y%m%d") + "-1",
        server_default=text("TO_CHAR(timezone('utc', now()), 'YYYYMMDD') || '-1'"),
    )

    # Periodicity columns
    periodicity = Column(String(10))  # Options: ONCE, DAILY, WEEKLY, WEEKDAYS, MONTHLY, ALWAYS
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    selected_date = Column(Date, nullable=True)
    event_type = Column(ENUM("activity", "flow", name="event_type_enum", create_type=False), nullable=False)
    activity_id = Column(UUID(as_uuid=True), nullable=True)
    activity_flow_id = Column(UUID(as_uuid=True), nullable=True)


class EventSchema(_BaseEventSchema, Base):
    __tablename__ = "events"

    applet_id = Column(ForeignKey("applets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)


class EventHistorySchema(_BaseEventSchema, HistoryAware, Base):
    __tablename__ = "event_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(UUID(as_uuid=True))
    user_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)


class AppletEventsSchema(Base):
    __tablename__ = "applet_events"

    applet_id = Column(ForeignKey("applet_histories.id_version", ondelete="CASCADE"), nullable=False)
    event_id = Column(ForeignKey("event_histories.id_version", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "applet_id",
            "event_id",
            "is_deleted",
            name="_unique_applet_events",
        ),
    )


class _BaseNotificationSchema:
    from_time = Column(Time, nullable=True)
    to_time = Column(Time, nullable=True)
    at_time = Column(Time, nullable=True)
    trigger_type = Column(String(10), nullable=False)  # fixed, random
    order = Column(Integer, nullable=True)


class NotificationSchema(_BaseNotificationSchema, Base):
    __tablename__ = "notifications"

    event_id = Column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)


class NotificationHistorySchema(_BaseNotificationSchema, HistoryAware, Base):
    __tablename__ = "notification_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(UUID(as_uuid=True))
    event_id = Column(ForeignKey("event_histories.id_version", ondelete="RESTRICT"), nullable=False)


class _BaseReminderSchema:
    activity_incomplete = Column(Integer, nullable=False)
    reminder_time = Column(Time, nullable=False)


class ReminderSchema(_BaseReminderSchema, Base):
    __tablename__ = "reminders"

    event_id = Column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)


class ReminderHistorySchema(_BaseReminderSchema, HistoryAware, Base):
    __tablename__ = "reminder_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(UUID(as_uuid=True))
    event_id = Column(ForeignKey("event_histories.id_version", ondelete="RESTRICT"), nullable=False)


class UserDeviceEventsSchema(Base):
    __tablename__ = "user_device_events"

    unique_constraint = "_unique_user_device_events"

    device_id = Column(UUID(as_uuid=True), ForeignKey("user_devices.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(13), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "event_id",
            "version",
            name=unique_constraint,
        ),
    )
