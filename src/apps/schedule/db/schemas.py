from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Interval,
    String,
    Time,
    UniqueConstraint,
)

from infrastructure.database.base import Base


class PeriodicitySchema(Base):
    __tablename__ = "periodicity"

    type = Column(
        String(10), nullable=False
    )  # Options: ONCE, DAILY, WEEKLY, WEEKDAYS, MONTHLY
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    interval = Column(Integer, nullable=False)
    # If type is Weekly, interval is 1-7;
    # If type is Monthly, interval is 1-31;
    # Otherwise interval is 0;


class EventSchema(Base):
    __tablename__ = "events"

    periodicity_id = Column(
        ForeignKey("periodicity.id", ondelete="RESTRICT"), nullable=False
    )
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    all_day = Column(Boolean, nullable=False, default=False)
    access_before_schedule = Column(Boolean, nullable=False)
    one_time_completion = Column(Boolean, nullable=False)
    timer = Column(Interval, nullable=False)
    timer_type = Column(String(10), nullable=False)  # NOT_SET, TIMER, IDLE
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )


class UserEventsSchema(Base):
    __tablename__ = "user_events"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_id = Column(
        ForeignKey("events.id", ondelete="RESTRICT"), nullable=False
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

    activity_id = Column(
        ForeignKey("activities.id", ondelete="RESTRICT"), nullable=False
    )
    event_id = Column(
        ForeignKey("events.id", ondelete="RESTRICT"), nullable=False
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

    flow_id = Column(
        ForeignKey("flows.id", ondelete="RESTRICT"), nullable=False
    )
    event_id = Column(
        ForeignKey("events.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "flow_id",
            "event_id",
            "is_deleted",
            name="_unique_flow_events",
        ),
    )
