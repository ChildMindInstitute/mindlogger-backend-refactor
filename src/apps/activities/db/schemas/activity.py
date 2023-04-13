from sqlalchemy import (
    REAL,
    Boolean,
    Column,
    ForeignKey,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base

__all__ = ["ActivitySchema", "ActivityHistorySchema"]


class _BaseActivitySchema:
    name = Column(String(length=100))
    description = Column(JSONB())
    splash_screen = Column(Text())
    image = Column(Text())
    show_all_at_once = Column(Boolean(), default=False)
    is_skippable = Column(Boolean(), default=False)
    is_reviewable = Column(Boolean(), default=False)
    response_is_editable = Column(Boolean(), default=False)
    order = Column(REAL())
    is_hidden = Column(Boolean(), default=False)


class ActivitySchema(Base, _BaseActivitySchema):
    __tablename__ = "activities"

    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )
    extra_fields = Column(
        JSONB(), default=dict, server_default=text("'{}'::jsonb")
    )


class ActivityHistorySchema(Base, _BaseActivitySchema):
    __tablename__ = "activity_histories"

    id = Column(UUID(as_uuid=True))
    id_version = Column(String(), primary_key=True)
    applet_id = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
