from sqlalchemy import REAL, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base

__all__ = ["ActivityItemSchema", "ActivityItemHistorySchema"]


class _BaseActivityItemSchema:
    question = Column(JSONB())
    response_type = Column(Text())
    answers = Column(JSONB())
    color_palette = Column(Text())
    timer = Column(Integer())
    has_token_value = Column(Boolean(), default=False)
    is_skippable = Column(Boolean(), default=False)
    has_alert = Column(Boolean(), default=False)
    has_score = Column(Boolean(), default=False)
    is_random = Column(Boolean(), default=False)
    is_able_to_move_to_previous = Column(Boolean(), default=False)
    has_text_response = Column(Boolean(), default=False)
    ordering = Column(REAL())


class ActivityItemSchema(_BaseActivityItemSchema, Base):
    __tablename__ = "activity_items"

    activity_id = Column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False
    )


class ActivityItemHistorySchema(_BaseActivityItemSchema, Base):
    __tablename__ = "activity_item_histories"

    id = Column(UUID(as_uuid=True))
    id_version = Column(String(), primary_key=True)
    activity_id = Column(
        ForeignKey("activity_histories.id_version", ondelete="CASCADE"),
        nullable=False,
    )
