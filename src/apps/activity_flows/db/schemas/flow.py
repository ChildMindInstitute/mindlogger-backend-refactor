from sqlalchemy import REAL, Boolean, Column, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database import Base

__all__ = ["ActivityFlowSchema", "ActivityFlowHistoriesSchema"]


class _BaseActivityFlowSchema:
    name = Column(Text())
    description = Column(JSONB())
    is_single_report = Column(Boolean(), default=False)
    hide_badge = Column(Boolean(), default=False)
    order = Column(REAL())
    is_hidden = Column(Boolean(), default=False)


class ActivityFlowSchema(_BaseActivityFlowSchema, Base):
    __tablename__ = "flows"

    applet_id = Column(ForeignKey("applets.id", ondelete="RESTRICT"))
    extra_fields = Column(
        JSONB(), default=dict, server_default=text("'{}'::jsonb")
    )


class ActivityFlowHistoriesSchema(_BaseActivityFlowSchema, Base):
    __tablename__ = "flow_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(UUID(as_uuid=True))
    applet_id = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT")
    )
