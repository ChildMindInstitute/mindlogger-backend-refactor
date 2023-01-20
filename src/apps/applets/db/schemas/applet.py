from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from infrastructure.database.base import Base

__all__ = ["AppletSchema", "AppletHistorySchema"]


class _BaseAppletSchema:
    display_name = Column(String(100), unique=True)
    description = Column(JSONB())
    about = Column(JSONB())
    image = Column(String(255))
    watermark = Column(String(255))

    theme_id = Column(Integer())
    version = Column(String(255))

    account_id = Column(Integer())

    report_server_ip = Column(Text())
    report_public_key = Column(Text())
    report_recipients = Column(JSONB())
    report_include_user_id = Column(Boolean(), default=False)
    report_include_case_id = Column(Boolean(), default=False)
    report_email_body = Column(Text())


class AppletSchema(_BaseAppletSchema, Base):
    __tablename__ = "applets"

    creator_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class AppletHistorySchema(_BaseAppletSchema, Base):
    __tablename__ = "applet_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(Integer())
    display_name = Column(String(length=100))

    creator_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
