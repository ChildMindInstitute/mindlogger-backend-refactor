import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base


class _BaseActivitySchema:
    guid = sa.Column(UUID(as_uuid=True))
    name = sa.Column(sa.String(length=100))
    description = sa.Column(JSONB())
    splash_screen = sa.Column(sa.Text())
    image = sa.Column(sa.Text())
    show_all_at_once = sa.Column(sa.Boolean(), default=False)
    is_skippable = sa.Column(sa.Boolean(), default=False)
    is_reviewable = sa.Column(sa.Boolean(), default=False)
    response_is_editable = sa.Column(sa.Boolean(), default=False)
    ordering = sa.Column(sa.REAL())


class ActivitySchema(Base, _BaseActivitySchema):
    __tablename__ = "activities"

    applet_id = sa.Column(
        sa.ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )
