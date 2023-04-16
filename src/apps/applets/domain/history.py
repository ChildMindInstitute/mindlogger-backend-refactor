from pydantic import Field

from apps.activities.domain import (
    ActivityHistoryChange,
    PublicActivityHistoryChange,
)
from apps.applets.domain.base import AppletBase
from apps.shared.domain import InternalModel, PublicModel

__all__ = ["AppletHistory", "AppletHistoryChange", "PublicAppletHistoryChange"]


class AppletHistory(AppletBase, InternalModel):
    pass


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
