from sqlalchemy import REAL, Column, ForeignKey, Integer, String

from infrastructure.database import Base


class _BaseActivityFlow:
    ordering = Column(REAL())


class ActivityFlowItemSchema(_BaseActivityFlow, Base):
    __tablename__ = "flow_items"

    activity_flow_id = Column(ForeignKey("flows.id", ondelete="RESTRICT"))
    activity_id = Column(ForeignKey("activities.id", ondelete="RESTRICT"))


class ActivityFlowItemHistorySchema(_BaseActivityFlow, Base):
    __tablename__ = "flow_item_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(Integer())
    activity_flow_id = Column(
        ForeignKey("flow_histories.id_version", ondelete="RESTRICT")
    )
    activity_id = Column(
        ForeignKey("activity_histories.id_version", ondelete="RESTRICT")
    )
