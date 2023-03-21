from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Interval,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database.base import Base


class PeriodicitySchema(Base):
    __tablename__ = "periodicity"

    type = Column(
        String(10), nullable=False
    )  # Options: ONCE, DAILY, WEEKLY, WEEKDAYS, MONTHLY, ALWAYS
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    selected_date = Column(Date, nullable=True)


class EventSchema(Base):
    __tablename__ = "events"

    periodicity_id = Column(
        ForeignKey("periodicity.id", ondelete="RESTRICT"), nullable=False
    )
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    access_before_schedule = Column(Boolean, nullable=True)
    one_time_completion = Column(Boolean, nullable=True)
    timer = Column(Interval, nullable=True)
    timer_type = Column(String(10), nullable=False)  # NOT_SET, TIMER, IDLE
    applet_id = Column(
        ForeignKey("applets.id", ondelete="CASCADE"), nullable=False
    )


class UserEventsSchema(Base):
    __tablename__ = "user_events"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_id = Column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_id",
            "is_deleted",
            name="_unique_user_events",
        ),
    )


class ActivityEventsSchema(Base):
    __tablename__ = "activity_events"

    activity_id = Column(UUID(as_uuid=True), nullable=False)
    event_id = Column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "event_id",
            "is_deleted",
            name="_unique_activity_events",
        ),
    )


class FlowEventsSchema(Base):
    __tablename__ = "flow_events"

    flow_id = Column(UUID(as_uuid=True), nullable=False)
    event_id = Column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "flow_id",
            "event_id",
            "is_deleted",
            name="_unique_flow_events",
        ),
    )
