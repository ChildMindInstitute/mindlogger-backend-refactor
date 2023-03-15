from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base


class AnswerActivityItemsSchema(Base):
    """This table is used as responses to specific activity items"""

    __tablename__ = "answers_activity_items"

    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    answer = Column(Text())
    applet_id = Column(UUID(as_uuid=True))
    applet_history_id = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_history_id = Column(
        ForeignKey("activity_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_item_history_id = Column(
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
    applet_id = Column(UUID(as_uuid=True))
    applet_history_id = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    flow_history_id = Column(
        ForeignKey("flow_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_history_id = Column(
        ForeignKey("activity_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_item_history_id = Column(
        ForeignKey("activity_item_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
