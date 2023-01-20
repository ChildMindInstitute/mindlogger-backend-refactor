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
    theme_id: int | None
    version: str
    account_id: int
    creator_id: int
    report_server_ip: str
    report_public_key: str
    report_recipients: str
    report_include_user_id: str
    report_include_case_id: str
    report_email_body: str


class AppletHistoryChange(AppletHistory):
    display_name: str | None
    description: dict | None
    about: dict | None
    image: str | None
    watermark: str | None
    theme_id: str | None
    version: str | None
    account_id: str | None
    creator_id: str | None
    report_server_ip: str | None
    report_public_key: str | None
    report_recipients: str | None
    report_include_user_id: str | None
    report_include_case_id: str | None
    report_email_body: str | None
    activity_changes: list[ActivityHistoryChange] = Field(default_factory=list)


class PublicAppletHistoryChange(PublicModel, AppletHistoryChange):
    activity_changes: list[PublicActivityHistoryChange] = Field(
        default_factory=list
    )
