from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base


class AnswerSchema(Base):
    __tablename__ = "answers"

    applet_id = Column(UUID(as_uuid=True))
    version = Column(Text())
    submit_id = Column(UUID(as_uuid=True))
    client = Column(JSONB())
    applet_history_id = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    flow_history_id = Column(
        ForeignKey("flow_histories.id_version", ondelete="RESTRICT"),
        nullable=True,
    )
    activity_history_id = Column(
        ForeignKey("activity_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    is_flow_completed = Column(Boolean(), nullable=True)
    migrated_data = Column(JSONB())


class AnswerNoteSchema(Base):
    __tablename__ = "answer_notes"

    answer_id = Column(
        ForeignKey("answers.id", ondelete="CASCADE"),
    )
    activity_id = Column(UUID(as_uuid=True))
    note = Column(Text())
    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    user_public_key = Column(Text())


class AnswerItemSchema(Base):
    __tablename__ = "answers_items"

    answer_id = Column(
        ForeignKey("answers.id", ondelete="CASCADE"),
    )
    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    answer = Column(Text())
    events = Column(Text())
    item_ids = Column(JSONB())
    identifier = Column(Text())
    user_public_key = Column(Text())
    scheduled_datetime = Column(DateTime())
    start_datetime = Column(DateTime(), nullable=False)
    end_datetime = Column(DateTime(), nullable=False)
    scheduled_event_id = Column(Text(), nullable=True)
    local_end_date = Column(Date(), nullable=True, index=True)
    local_end_time = Column(Time, nullable=True)
    is_assessment = Column(Boolean())
    migrated_data = Column(JSONB())
