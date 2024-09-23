from sqlalchemy import REAL, Boolean, Column, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from infrastructure.database import Base

__all__ = ["ActivityFlowSchema", "ActivityFlowHistoriesSchema"]


class _BaseActivityFlowSchema:
    name = Column(Text())
    description = Column(JSONB())
    is_single_report = Column(Boolean(), default=False)
    hide_badge = Column(Boolean(), default=False)
    report_included_activity_name = Column(Text(), nullable=True)
    report_included_item_name = Column(Text(), nullable=True)
    order = Column(REAL())
    is_hidden = Column(Boolean(), default=False)
    extra_fields = Column(JSONB(), default=dict, server_default=text("'{}'::jsonb"))
    auto_assign = Column(Boolean(), default=True)


class ActivityFlowSchema(_BaseActivityFlowSchema, Base):
    __tablename__ = "flows"

    applet_id = Column(ForeignKey("applets.id", ondelete="RESTRICT"))


class ActivityFlowHistoriesSchema(_BaseActivityFlowSchema, Base):
    __tablename__ = "flow_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(UUID(as_uuid=True))
    applet_id = Column(ForeignKey("applet_histories.id_version", ondelete="RESTRICT"))

    items = relationship(
        "ActivityFlowItemHistorySchema",
        order_by="asc(ActivityFlowItemHistorySchema.order)",
        lazy="noload",
    )
