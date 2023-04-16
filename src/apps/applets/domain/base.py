import datetime
import uuid

from pydantic import BaseModel, Field

from apps.shared.enums import Language


class AppletBase(BaseModel):
    display_name: str
    description: dict[Language, str] = Field(default_factory=dict)
    about: dict[Language, str] = Field(default_factory=dict)
    image: str = ""
    watermark: str = ""
    theme_id: uuid.UUID | None = None
    report_server_ip: str = ""
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""
    link: uuid.UUID | None
    require_login: bool | None
    pinned_at: datetime.datetime | None
    retention_period: int | None
    retention_type: str | None


class AppletFetchBase(AppletBase):
    id: uuid.UUID
    version: str
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None
