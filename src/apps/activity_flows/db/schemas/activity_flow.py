import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database import Base


class ActivityFlowSchema(Base):
    __tablename__ = "flows"

    name = sa.Column(sa.Text())
    guid = sa.Column(UUID(as_uuid=True))
    description = sa.Column(JSONB())
    applet_id = sa.Column(sa.ForeignKey("applets.id", ondelete="RESTRICT"))
    is_single_report = sa.Column(sa.Boolean(), default=False)
    hide_badge = sa.Column(sa.Boolean(), default=False)
    ordering = sa.Column(sa.REAL())
