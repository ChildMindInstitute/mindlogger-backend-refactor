import datetime
import uuid

from pydantic import field_validator, BaseModel, Field, IPvAnyAddress, PositiveInt

from apps.shared.domain import InternalModel
from apps.shared.domain.custom_validations import sanitize_string
from apps.shared.enums import Language


class AppletReportConfigurationBase(BaseModel):
    report_server_ip: str = ""
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""

    @field_validator("report_email_body")
    @classmethod
    def validate_string(cls, value):
        return sanitize_string(value)


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
    link: uuid.UUID | None = None
    require_login: bool | None = None
    pinned_at: datetime.datetime | None = None
    retention_period: int | None = None
    retention_type: str | None = None
    stream_enabled: bool | None = None
    stream_ip_address: IPvAnyAddress | None = None
    stream_port: PositiveInt | None = None

    @field_validator("description", "about")
    @classmethod
    def validate_dict(cls, value):
        if isinstance(value, dict):
            for key in value:
                value[key] = sanitize_string(value[key])
        elif isinstance(value, str):
            value = sanitize_string(value)
        return value

    @field_validator("display_name")
    @classmethod
    def validate_string(cls, value):
        return sanitize_string(value)


class AppletBase(AppletBaseInfo):
    encryption: Encryption


class AppletFetchBase(AppletReportConfigurationBase, AppletBaseInfo):
    encryption: Encryption | None = None
    id: uuid.UUID
    version: str
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None
    is_published: bool = False
    owner_id: uuid.UUID | None = None
    integrations: list[str] | None = None
