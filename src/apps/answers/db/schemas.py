from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    Time,
    Unicode,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from infrastructure.database.base import Base


class AnswerSchema(Base):
    __tablename__ = "answers"

    applet_id = Column(UUID(as_uuid=True), index=True)
    version = Column(Text())
    submit_id = Column(UUID(as_uuid=True))
    client = Column(JSONB())
    applet_history_id = Column(Text(), nullable=False, index=True)
    flow_history_id = Column(Text(), nullable=True, index=True)
    activity_history_id = Column(Text(), nullable=False, index=True)
    respondent_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    is_flow_completed = Column(Boolean(), nullable=True)
    migrated_data = Column(JSONB())
    target_subject_id = Column(Text(), nullable=False, index=True)
    source_subject_id = Column(Text(), nullable=False, index=True)
    relation = Column(String(length=20), unique=True)


class AnswerNoteSchema(Base):
    __tablename__ = "answer_notes"

    answer_id = Column(UUID(as_uuid=True), index=True)
    activity_id = Column(UUID(as_uuid=True))
    note = Column(StringEncryptedType(Unicode, get_key))
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)


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
    scheduled_event_id = Column(Text(), nullable=True)
    local_end_date = Column(Date(), nullable=True, index=True)
    local_end_time = Column(Time, nullable=True)
    is_assessment = Column(Boolean())
    migrated_data = Column(JSONB())
    assessment_activity_id = Column(Text(), nullable=True, index=True)
