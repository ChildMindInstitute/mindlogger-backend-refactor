import uuid

from pydantic import Field, IPvAnyAddress, PositiveInt

from apps.activities.domain import (
    ActivityHistoryChange,
    PublicActivityHistoryChange,
)
from apps.activity_flows.domain import (
    ActivityFlowHistoryChange,
    PublicActivityFlowHistoryChange,
)
from apps.shared.domain import InternalModel, PublicModel
from apps.shared.enums import Language

__all__ = ["AppletHistory", "AppletHistoryChange", "PublicAppletHistoryChange"]


class AppletHistory(InternalModel):
    display_name: str
    description: dict[Language, str] = Field(
        default_factory=lambda: {Language.ENGLISH: ""}
    )
    about: dict[Language, str] = Field(
        default_factory=lambda: {Language.ENGLISH: ""}
    )
    image: str = ""
    watermark: str = ""
    theme_id: uuid.UUID | None = None
    report_server_ip: str = ""
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""
    stream_enabled: bool | None = None
    stream_ip_address: IPvAnyAddress | None = None
    stream_port: PositiveInt | None = None
    version: str


class AppletHistoryChange(InternalModel):
    """
    Model to show changed for indicated fields
    For example:
        display_name: "Display name is changed from A to B"
    """

    display_name: str | None = None
    changes: list[str] = Field(default_factory=list)
    activities: list[ActivityHistoryChange] = Field(default_factory=list)
    activity_flows: list[ActivityFlowHistoryChange] = Field(
        default_factory=list
    )


class PublicAppletHistoryChange(PublicModel):
    """
    Model to show changed for indicated fields
    For example:
        display_name: "Display name is changed from A to B"
    """

    display_name: str | None = None
    changes: list[str] | None = Field(default_factory=list)
    activities: list[PublicActivityHistoryChange] = Field(default_factory=list)
    activity_flows: list[PublicActivityFlowHistoryChange] = Field(
        default_factory=list
    )
