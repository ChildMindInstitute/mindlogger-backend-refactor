from sqlalchemy import REAL, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base


class _BaseActivitySchema:
    guid = Column(UUID(as_uuid=True))
    name = Column(String(length=100))
    description = Column(JSONB())
    splash_screen = Column(Text())
    image = Column(Text())
    show_all_at_once = Column(Boolean(), default=False)
    is_skippable = Column(Boolean(), default=False)
    is_reviewable = Column(Boolean(), default=False)
    response_is_editable = Column(Boolean(), default=False)
    ordering = Column(REAL())


class ActivitySchema(Base, _BaseActivitySchema):
    __tablename__ = "activities"

    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )


class ActivityHistorySchema(Base, _BaseActivitySchema):
    __tablename__ = "activity_histories"

    id = Column(Integer())
    id_version = Column(String(), primary_key=True)
    applet_id = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
