from sqlalchemy import REAL, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database import Base


class _BaseActivityFlowSchema:
    name = Column(Text())
    guid = Column(UUID(as_uuid=True))
    description = Column(JSONB())
    is_single_report = Column(Boolean(), default=False)
    hide_badge = Column(Boolean(), default=False)
    ordering = Column(REAL())


class ActivityFlowSchema(_BaseActivityFlowSchema, Base):
    __tablename__ = "flows"

    applet_id = Column(ForeignKey("applets.id", ondelete="RESTRICT"))


class ActivityFlowHistoriesSchema(_BaseActivityFlowSchema, Base):
    __tablename__ = "flow_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(Integer())
    applet_id = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT")
    )
