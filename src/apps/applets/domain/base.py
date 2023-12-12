import datetime
import uuid

from pydantic import BaseModel, Field, IPvAnyAddress, PositiveInt

from apps.shared.domain import InternalModel
from apps.shared.enums import Language


class AppletReportConfigurationBase(BaseModel):
    report_server_ip: str = ""
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""


class Encryption(InternalModel):
    public_key: str
    prime: str
    base: str
    account_id: str


class AppletBaseInfo(BaseModel):
    display_name: str
    description: dict[Language, str] = Field(default_factory=dict)
    about: dict[Language, str] = Field(default_factory=dict)
    image: str = ""
    watermark: str = ""
    theme_id: uuid.UUID | None = None
    link: uuid.UUID | None
    require_login: bool | None
    pinned_at: datetime.datetime | None
    retention_period: int | None
    retention_type: str | None
    stream_enabled: bool | None
    stream_ip_address: IPvAnyAddress | None
    stream_port: PositiveInt | None
    integrations: list[str]


class AppletBase(AppletBaseInfo):
    encryption: Encryption


class AppletFetchBase(AppletReportConfigurationBase, AppletBaseInfo):
    encryption: Encryption | None
    id: uuid.UUID
    version: str
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None
    is_published: bool = False
