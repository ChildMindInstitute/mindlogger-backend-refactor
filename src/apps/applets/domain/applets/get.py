import pydantic.types as types
from pydantic import Field

import apps.activities.domain as activity_domain
import apps.activity_flows.domain as flow_domain
import apps.shared.domain as base_domain


class Applet(base_domain.InternalModel):
    id: int
    display_name: str
    version: str
    description: types.Dict[str, str] = dict()
    about: types.Dict[str, str] = dict()
    image: str = ""
    watermark: str = ""
    theme_id: types.NonNegativeInt = 0
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: types.List[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""

    activities: types.List[activity_domain.Activity] = Field(
        default_factory=list
    )
    activity_flows: types.List[flow_domain.ActivityFlow] = Field(
        default_factory=list
    )


class PublicApplet(base_domain.PublicModel):
    """Public user data model."""

    id: int
    display_name: str
    version: str
    description: types.Dict[str, str] = dict()
    about: types.Dict[str, str] = dict()
    image: str = ""
    watermark: str = ""
    theme_id: types.NonNegativeInt = 0
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: types.List[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""

    activities: types.List[activity_domain.Activity] = Field(
        default_factory=list
    )
    activity_flows: types.List[flow_domain.ActivityFlow] = Field(
        default_factory=list
    )

    def __str__(self) -> str:
        return self.display_name
