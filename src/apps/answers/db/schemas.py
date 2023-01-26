from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from infrastructure.database.base import Base


class AnswerSchema(Base):
    __tablename__ = "answers"

    applet_history_id_version = Column(
        ForeignKey("applet_history.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_history_id_version = Column(
        ForeignKey("activity_history.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_item_history_id_version = Column(
        ForeignKey("activity_item_history.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    flow_history_id_version = Column(
        ForeignKey("flow_history.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    flow_item_history_id_version = Column(
        ForeignKey("flow_item_history.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    answer = Column(JSONB())
