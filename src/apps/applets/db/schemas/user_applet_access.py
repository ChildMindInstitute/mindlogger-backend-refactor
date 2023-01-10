import sqlalchemy as sa

from infrastructure.database.base import Base


class UserAppletAccessSchema(Base):
    __tablename__ = "user_applet_accesses"

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    applet_id = sa.Column(
        sa.ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )
    role = sa.Column(sa.String(length=20), nullable=False)
