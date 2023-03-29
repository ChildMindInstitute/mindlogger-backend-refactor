from sqlalchemy import REAL, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database import Base

__all__ = ["ActivityFlowItemSchema", "ActivityFlowItemHistorySchema"]


class _BaseActivityFlow:
    order = Column(REAL())


class ActivityFlowItemSchema(_BaseActivityFlow, Base):
    __tablename__ = "flow_items"

    activity_flow_id = Column(ForeignKey("flows.id", ondelete="RESTRICT"))
    activity_id = Column(ForeignKey("activities.id", ondelete="RESTRICT"))


class ActivityFlowItemHistorySchema(_BaseActivityFlow, Base):
    __tablename__ = "flow_item_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(UUID(as_uuid=True))
    activity_flow_id = Column(
        ForeignKey("flow_histories.id_version", ondelete="RESTRICT")
    )
    activity_id = Column(
        ForeignKey("activity_histories.id_version", ondelete="RESTRICT")
    )
