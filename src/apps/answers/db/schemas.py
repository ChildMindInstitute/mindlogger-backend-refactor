from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    Unicode,
    and_,
    asc,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from infrastructure.database.base import Base
from infrastructure.database.mixins import HistoryAware


class AnswerSchema(HistoryAware, Base):
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
    target_subject_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    source_subject_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    input_subject_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    relation = Column(String(length=20), nullable=True)
    consent_to_share = Column(Boolean(), default=False)
    event_history_id = Column(String(), nullable=True, index=True)
    device_id = Column(Text(), nullable=True, index=True)

    answer_item = relationship(
        "AnswerItemSchema",
        order_by=lambda: asc(AnswerItemSchema.created_at),
        primaryjoin=(
            lambda: and_(AnswerSchema.id == AnswerItemSchema.answer_id, AnswerItemSchema.is_assessment.isnot(True))  # type: ignore[has-type]
        ),
        uselist=False,
        lazy="noload",
    )


class AnswerNoteSchema(Base):
    __tablename__ = "answer_notes"

    answer_id = Column(UUID(as_uuid=True), index=True)
    flow_submit_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    activity_id = Column(UUID(as_uuid=True), nullable=True)
    activity_flow_id = Column(UUID(as_uuid=True), nullable=True)
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
    tz_offset = Column(Integer, nullable=True, comment="Local timezone offset in minutes")
    reviewed_flow_submit_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    @hybrid_property
    def is_identifier_encrypted(self):
        return (self.migrated_data or {}).get("is_identifier_encrypted") is not False

    @is_identifier_encrypted.expression  # type: ignore[no-redef]
    def is_identifier_encrypted(cls):
        return cls.migrated_data[text("'is_identifier_encrypted'")].astext.cast(Boolean()).isnot(false())
