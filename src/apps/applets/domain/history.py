import uuid

from pydantic import Field

from apps.activities.domain import (
    ActivityHistoryChange,
    PublicActivityHistoryChange,
)
from apps.shared.domain import InternalModel, PublicModel

__all__ = ["AppletHistory", "AppletHistoryChange", "PublicAppletHistoryChange"]


class AppletHistory(InternalModel):
    display_name: str
    description: dict
    about: dict
    image: str
    watermark: str
    theme_id: uuid.UUID | None
    version: str
    report_server_ip: str
    report_public_key: str
    report_recipients: list[str]
    report_include_user_id: str
    report_include_case_id: str
    report_email_body: str


class AppletHistoryChange(InternalModel):
    """
    Model to show changed for indicated fields
    For example:
        display_name: "Display name is changed from A to B"
        account_id: "Update by user B"
    """

    display_name: str | None = None
    description: dict | None = None
    about: dict | None = None
    image: str | None = None
    watermark: str | None = None
    theme_id: str | None = None
    version: str | None = None
    account_id: str | None = None
    creator_id: str | None = None
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
        account_id: "Update by user B"
    """

    display_name: str | None = None
    description: dict | None = None
    about: dict | None = None
    image: str | None = None
    watermark: str | None = None
    theme_id: str | None = None
    version: str | None = None
    account_id: str | None = None
    creator_id: str | None = None
    report_server_ip: str | None = None
    report_public_key: str | None = None
    report_recipients: list[str] | None = None
    report_include_user_id: str | None = None
    report_include_case_id: str | None = None
    report_email_body: str | None = None
    activities: list[PublicActivityHistoryChange] = Field(default_factory=list)
