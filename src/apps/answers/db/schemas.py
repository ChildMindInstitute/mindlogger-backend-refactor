from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base


class AnswerSchema(Base):
    __tablename__ = "answers"

    applet_id = Column(UUID(as_uuid=True))
    version = Column(Text())
    submit_id = Column(UUID(as_uuid=True))
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
    is_assessment = Column(Boolean())
