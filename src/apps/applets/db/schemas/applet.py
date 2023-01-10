import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from infrastructure.database.base import Base


class _BaseAppletSchema:
    display_name = sa.Column(sa.String(length=100), unique=True)
    description = sa.Column(JSONB())
    about = sa.Column(JSONB())
    image = sa.Column(sa.String(255))
    watermark = sa.Column(sa.String(255))

    theme_id = sa.Column(sa.Integer())
    version = sa.Column(sa.String(255))

    creator_id = sa.Column(sa.Integer())
    account_id = sa.Column(sa.Integer())

    report_server_ip = sa.Column(sa.Text())
    report_public_key = sa.Column(sa.Text())
    report_recipients = sa.Column(JSONB())
    report_include_user_id = sa.Column(sa.Boolean(), default=False)
    report_include_case_id = sa.Column(sa.Boolean(), default=False)
    report_email_body = sa.Column(sa.Text())


class AppletSchema(_BaseAppletSchema, Base):
    __tablename__ = "applets"
