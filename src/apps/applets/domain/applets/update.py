import pydantic.types as types
from pydantic import Field

import apps.activities.domain as activity_domain
import apps.activity_flows.domain as flow_domain
from apps.shared.domain import InternalModel


class AppletUpdate(InternalModel):
    display_name: str
    description: types.Dict[str, types.Any]
    about: types.Dict[str, types.Any]
    image: str = ""
    watermark: str = ""
    theme_id: types.PositiveInt = 0
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: types.List[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""

    activities: types.List[activity_domain.ActivityUpdate]
    activity_flows: types.List[flow_domain.ActivityFlowUpdate]
