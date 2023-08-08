from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base


class AnswerSchema(Base):
    __tablename__ = "answers"

    applet_id = Column(UUID(as_uuid=True))
    version = Column(Text())
    submit_id = Column(UUID(as_uuid=True))
    client = Column(JSONB())
    applet_history_id = Column(Text(), nullable=False, index=True)
    flow_history_id = Column(Text(), nullable=True, index=True)
    activity_history_id = Column(Text(), nullable=False, index=True)
    respondent_id = Column(UUID(as_uuid=True), nullable=True, index=True)


class AnswerNoteSchema(Base):
    __tablename__ = "answer_notes"

    answer_id = Column(
        ForeignKey("answers.id", ondelete="CASCADE"),
    )
    activity_id = Column(UUID(as_uuid=True))
    note = Column(Text())
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_public_key = Column(Text())


class AnswerItemSchema(Base):
    __tablename__ = "answers_items"

    answer_id = Column(
        ForeignKey("answers.id", ondelete="CASCADE"),
    )
    respondent_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    answer = Column(Text())
    events = Column(Text())
    item_ids = Column(JSONB())
    identifier = Column(Text())
    user_public_key = Column(Text())
    scheduled_datetime = Column(DateTime())
    start_datetime = Column(DateTime(), nullable=False)
    end_datetime = Column(DateTime(), nullable=False)
    is_assessment = Column(Boolean())
