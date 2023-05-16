from sqlalchemy import REAL, Boolean, Column, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base

__all__ = ["ActivityItemSchema", "ActivityItemHistorySchema"]


class _BaseActivityItemSchema:
    name = Column(Text(), nullable=False)
    question = Column(JSONB())
    response_type = Column(Text())
    response_values = Column(JSONB())
    config = Column(JSONB(), default=dict())
    order = Column(REAL())
    is_hidden = Column(Boolean(), default=False)
    conditional_logic = Column(JSONB())


class ActivityItemSchema(_BaseActivityItemSchema, Base):
    __tablename__ = "activity_items"

    activity_id = Column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False
    )
    extra_fields = Column(
        JSONB(), default=dict, server_default=text("'{}'::jsonb")
    )


class ActivityItemHistorySchema(_BaseActivityItemSchema, Base):
    __tablename__ = "activity_item_histories"

    id = Column(UUID(as_uuid=True))
    id_version = Column(String(), primary_key=True)
    activity_id = Column(
        ForeignKey("activity_histories.id_version", ondelete="CASCADE"),
        nullable=False,
    )
