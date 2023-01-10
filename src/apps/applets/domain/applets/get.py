from pydantic import Field
from pydantic.types import PositiveInt

from apps.activities.domain import Activity
from apps.activity_flows.domain import ActivityFlow
from apps.shared import domain


class Applet(domain.InternalModel):
    id: int
    display_name: str
    version: str
    description: dict[str, str] = Field(default_factory=dict)
    about: dict[str, str] = Field(default_factory=dict)
    image: str = ""
    watermark: str = ""
    theme_id: PositiveInt = 0
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""

    activities: list[Activity] = Field(default_factory=list)
    activity_flows: list[ActivityFlow] = Field(default_factory=list)


class PublicApplet(domain.PublicModel):
    """Public user data model."""

    id: int
    display_name: str
    version: str
    description: dict[str, str] = Field(default_factory=dict)
    about: dict[str, str] = Field(default_factory=dict)
    image: str = ""
    watermark: str = ""
    theme_id: PositiveInt = 0
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""

    activities: list[Activity] = Field(default_factory=list)
    activity_flows: list[ActivityFlow] = Field(default_factory=list)

    def __str__(self) -> str:
        return self.display_name
