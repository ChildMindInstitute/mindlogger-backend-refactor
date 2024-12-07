from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy_utils.types import IPAddressType

from infrastructure.database.base import Base
from infrastructure.database.mixins import HistoryAware

__all__ = ["AppletSchema", "AppletHistorySchema"]


class _BaseAppletSchema:
    display_name = Column(String(100))
    description = Column(JSONB())
    about = Column(JSONB())
    image = Column(String(255))
    watermark = Column(String(255))

    theme_id = Column(UUID(as_uuid=True))
    version = Column(String(255))

    report_server_ip = Column(Text())
    report_public_key = Column(Text())
    report_recipients = Column(JSONB())
    report_include_user_id = Column(Boolean(), default=False)
    report_include_case_id = Column(Boolean(), default=False)
    report_email_body = Column(Text())
    extra_fields = Column(JSONB(), default=dict, server_default=text("'{}'::jsonb"))

    stream_enabled = Column(Boolean(), default=False)
    stream_ip_address = Column(IPAddressType())
    stream_port = Column(Integer())


class AppletSchema(_BaseAppletSchema, Base):
    __tablename__ = "applets"

    encryption = Column(JSONB())
    link = Column(UUID(as_uuid=True), unique=True)
    require_login = Column(Boolean(), default=True)
    pinned_at = Column(DateTime(), nullable=True)
    retention_period = Column(Integer(), nullable=True)
    retention_type = Column(String(20), nullable=True)
    is_published = Column(Boolean(), default=False)
    creator_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)


class AppletHistorySchema(_BaseAppletSchema, HistoryAware, Base):
    __tablename__ = "applet_histories"

    id_version = Column(String(), primary_key=True)
    id = Column(UUID(as_uuid=True))
    display_name = Column(String(length=100))

    user_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
