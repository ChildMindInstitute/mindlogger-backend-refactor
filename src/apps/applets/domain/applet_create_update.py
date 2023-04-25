from pydantic import Field

from apps.activities.domain.activity_create import ActivityCreate
from apps.activities.domain.activity_update import ActivityUpdate
from apps.activity_flows.domain.flow_create import FlowCreate
from apps.activity_flows.domain.flow_update import FlowUpdate
from apps.applets.domain.base import AppletBase
from apps.shared.domain import InternalModel


class AppletCreate(AppletBase, InternalModel):
    password: str
    activities: list[ActivityCreate]
    activity_flows: list[FlowCreate]
    extra_fields: dict = Field(default_factory=dict)


class AppletUpdate(AppletBase, InternalModel):
    password: str
    activities: list[ActivityUpdate]
    activity_flows: list[FlowUpdate]


class AppletDuplicateRequest(InternalModel):
    display_name: str
    password: str


class AppletPassword(InternalModel):
    password: str
