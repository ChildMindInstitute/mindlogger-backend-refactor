from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from infrastructure.database.base import Base


class AnswerActivityItemsSchema(Base):
    __tablename__ = "answers_activity_items"

    answer = Column(JSONB())
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_item_history_id_version = Column(
        ForeignKey("activity_item_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )


class AnswerFlowItemsSchema(Base):
    __tablename__ = "answers_flow_items"

    answer = Column(JSONB())
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    flow_item_history_id_version = Column(
        ForeignKey("flow_item_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
