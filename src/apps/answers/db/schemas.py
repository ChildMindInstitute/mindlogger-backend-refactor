from sqlalchemy import Boolean, Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base


class AnswerSchema(Base):
    __tablename__ = "answers"

    applet_id = Column(UUID(as_uuid=True))
    version = Column(Text())
    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    user_public_key = Column(Text())


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
    answer = Column(Text())
    events = Column(Text())
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
    item_ids = Column(JSONB())


class AssessmentAnswerItemSchema(Base):
    __tablename__ = "assessment_answer_items"

    answer_id = Column(
        ForeignKey("answers.id", ondelete="CASCADE"),
    )
    answer = Column(Text())
    applet_history_id = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_history_id = Column(
        ForeignKey("activity_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    item_ids = Column(JSONB())
    reviewer_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewer_public_key = Column(Text())
    is_edited = Column(Boolean(), default=False)
