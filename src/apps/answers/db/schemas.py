from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from infrastructure.database.base import Base


class AnswerActivityItemsSchema(Base):
    """This table is used as responses to specific activity items"""

    __tablename__ = "answers_activity_items"

    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    answer = Column(JSONB())
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    applet_history_id_version = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_id = Column(
        ForeignKey("activities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_item_history_id_version = Column(
        ForeignKey("activity_item_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )


class AnswerFlowItemsSchema(Base):
    """This table is used as responses to specific flow activity items"""

    __tablename__ = "answers_flow_items"

    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    answer = Column(JSONB())
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    applet_history_id_version = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    flow_item_history_id_version = Column(
        ForeignKey("flow_item_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_item_history_id_version = Column(
        ForeignKey("activity_item_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
