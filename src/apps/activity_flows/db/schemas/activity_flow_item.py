import sqlalchemy as sa
import sqlalchemy.orm

from apps.activity_flows.db.schemas.activity_flow import ActivityFlowSchema
from infrastructure.database import Base


class _BaseActivityFlow:
    ordering = sa.Column(sa.REAL())


class ActivityFlowItemSchema(_BaseActivityFlow, Base):
    __tablename__ = "flow_items"

    activity_flow_id = sa.Column(
        sa.ForeignKey("flows.id", ondelete="RESTRICT")
    )
    activity_id = sa.Column(sa.Integer())
    activity_flow = sa.orm.relation(ActivityFlowSchema)


class ActivityFlowItemHistorySchema(_BaseActivityFlow, Base):
    __tablename__ = "flow_item_histories"

    id_version = sa.Column(sa.String(), primary_key=True)
    id = sa.Column(sa.Integer())
    activity_flow_id = sa.Column(
        sa.ForeignKey("flow_histories.id_version", ondelete="RESTRICT")
    )
    activity_id = sa.Column(sa.String())
