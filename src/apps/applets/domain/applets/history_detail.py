import uuid
from typing import Annotated

from pydantic import Field

from apps.shared.domain import InternalModel


class ActivityItem(InternalModel):
    id: uuid.UUID
    id_version: str
    activity_id: str
    question: dict[str, str]
    response_type: str
    response_values: list | dict | None = None
    config: dict
    order: int
    name: str
    is_hidden: bool | None = False
    conditional_logic: dict | None = None
    allow_edit: bool | None = None


class Activity(InternalModel):
    id: uuid.UUID
    id_version: str
    applet_id: str
    name: str
    description: Annotated[dict[str, str], Field(default_factory=dict)]
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    order: int
    is_hidden: bool = False
    scores_and_reports: dict | None = None
    subscale_setting: dict | None = None
    items: Annotated[list[ActivityItem], Field(default_factory=list)]


class ActivityFlowItem(InternalModel):
    id: uuid.UUID
    id_version: str
    activity_flow_id: str
    activity_id: str
    order: int
    activity: Activity | None = None


class ActivityFlow(InternalModel):
    id: uuid.UUID
    id_version: str
    name: str
    applet_id: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    order: int
    items: Annotated[list[ActivityFlowItem], Field(default_factory=list)]


class Applet(InternalModel):
    id: uuid.UUID
    id_version: str
    display_name: str
    version: str
    description: Annotated[dict[str, str], Field(default_factory=dict)]
    about: Annotated[dict[str, str], Field(default_factory=dict)]
    image: str = ""
    watermark: str = ""
    theme_id: uuid.UUID | None = None
    report_server_ip: str = ""
    report_public_key: str = ""
    report_recipients: Annotated[list[str], Field(default_factory=list)]
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""
    activities: Annotated[list[Activity], Field(default_factory=list)]
    activity_flows: Annotated[list[ActivityFlow], Field(default_factory=list)]
