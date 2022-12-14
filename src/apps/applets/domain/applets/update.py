from pydantic import Field
from pydantic.types import PositiveInt

from apps.activities.domain import ActivityUpdate
from apps.activity_flows.domain import ActivityFlowUpdate
from apps.shared.domain import InternalModel


class AppletUpdate(InternalModel):
    display_name: str
    description: dict[str, str]
    about: dict[str, str]
    image: str = ""
    watermark: str = ""
    theme_id: PositiveInt | None = None
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""

    activities: list[ActivityUpdate]
    activity_flows: list[ActivityFlowUpdate]
