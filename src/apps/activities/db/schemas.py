from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, Text

from infrastructure.database.base import Base


class ActivitySchema(Base):
    __tablename__ = "activities"

    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )

    name = Column(String(length=100))
    description = Column(String(length=255))
    splash_screen = Column(Text)
    image = Column(Text)
    show_all_at_once = Column(Boolean, default=False)
    is_skippable = Column(Boolean, default=False)
    is_reviewable = Column(Boolean, default=False)
    response_is_editable = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)


class ActivityItemSchema(Base):
    __tablename__ = "activity_items"

    activity_id = Column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False
    )

    question = Column(Text)
    response_type = Column(Text)
    answers = Column(JSON)
    color_palette = Column(Text)
    timer = Column(Integer)
    has_token_value = Column(Boolean, default=False)
    is_skippable = Column(Boolean, default=False)
    has_alert = Column(Boolean, default=False)
    has_score = Column(Boolean, default=False)
    is_random = Column(Boolean, default=False)
    is_able_to_move_to_previous = Column(Boolean, default=False)
    has_text_response = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
