import sqlalchemy as sa

from infrastructure.database import Base


class ActivityFlowItemSchema(Base):
    __tablename__ = "flow_items"

    activity_flow_id = sa.Column(
        sa.ForeignKey("flows.id", ondelete="RESTRICT")
    )
    activity_id = sa.Column(sa.Integer())
    ordering = sa.Column(sa.REAL())
