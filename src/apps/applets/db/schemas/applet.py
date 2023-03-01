from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base

__all__ = ["AppletSchema", "AppletHistorySchema"]


class _BaseAppletSchema:
    display_name = Column(String(100), unique=True)
    description = Column(JSONB())
    about = Column(JSONB())
    image = Column(String(255))
    watermark = Column(String(255))

    theme_id = Column(UUID(as_uuid=True))
    version = Column(String(255))

    account_id = Column(UUID(as_uuid=True))

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
    folder_id = Column(ForeignKey("folders.id", ondelete="RESTRICT"))
    link = Column(UUID(as_uuid=True), unique=True)
    require_login = Column(Boolean(), default=True)
    pinned_at = Column(DateTime(), nullable=True)


class AppletHistorySchema(_BaseAppletSchema, Base):
    __tablename__ = "applet_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(UUID(as_uuid=True))
    display_name = Column(String(length=100))

    creator_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
