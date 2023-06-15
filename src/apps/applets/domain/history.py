from pydantic import Field
import uuid
import datetime
from apps.activities.domain import (
    ActivityHistoryChange,
    PublicActivityHistoryChange,
)
from apps.shared.enums import Language
from apps.shared.domain import InternalModel, PublicModel

__all__ = ["AppletHistory", "AppletHistoryChange", "PublicAppletHistoryChange"]


class AppletHistory(InternalModel):
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


class AppletHistoryChange(InternalModel):
    """
    Model to show changed for indicated fields
    For example:
        display_name: "Display name is changed from A to B"
    """

    display_name: str | None = None
    description: dict | str | None = None
    about: dict | str | None = None
    image: str | None = None
    watermark: str | None = None
    theme_id: str | None = None
    version: str | None = None
    report_server_ip: str | None = None
    report_public_key: str | None = None
    report_recipients: list[str] | None = None
    report_include_user_id: str | None = None
    report_include_case_id: str | None = None
    report_email_body: str | None = None
    activities: list[ActivityHistoryChange] = Field(default_factory=list)


class PublicAppletHistoryChange(PublicModel):
    """
    Model to show changed for indicated fields
    For example:
        display_name: "Display name is changed from A to B"
    """

    display_name: str | None = None
    description: dict | str | None = None
    about: dict | str | None = None
    image: str | None = None
    watermark: str | None = None
    theme_id: str | None = None
    version: str | None = None
    report_server_ip: str | None = None
    report_public_key: str | None = None
    report_recipients: list[str] | None = None
    report_include_user_id: str | None = None
    report_include_case_id: str | None = None
    report_email_body: str | None = None
    activities: list[PublicActivityHistoryChange] = Field(default_factory=list)
