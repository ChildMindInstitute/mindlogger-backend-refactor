from pydantic import root_validator

from apps.activities.domain.activity_create import ActivityCreate
from apps.activities.domain.activity_update import ActivityUpdate
from apps.activities.errors import (
    DuplicatedActivitiesError,
    DuplicatedActivityFlowsError,
)
from apps.activity_flows.domain.flow_create import FlowCreate
from apps.activity_flows.domain.flow_update import FlowUpdate
from apps.applets.domain.base import AppletBase
from apps.shared.domain import InternalModel


class AppletCreate(AppletBase, InternalModel):
    password: str
    activities: list[ActivityCreate]
    activity_flows: list[FlowCreate]


class AppletUpdate(AppletBase, InternalModel):
    password: str
    activities: list[ActivityUpdate]
    activity_flows: list[FlowUpdate]

    @root_validator()
    def validate_existing_ids_for_duplicate(cls, values):
        activities = values.get("activities", [])
        flows = values.get("activity_flows", [])

        activity_ids = set()
        flow_ids = set()
        for activity in activities:  # type:ActivityUpdate
            if activity.id and activity.id in activity_ids:
                raise DuplicatedActivitiesError()
            activity_ids.add(activity.id)

        for flow in flows:  # type:FlowUpdate
            if flow.id and flow.id in flow_ids:
                raise DuplicatedActivityFlowsError()
            flow_ids.add(flow.id)
        return values


class AppletDuplicateRequest(InternalModel):
    display_name: str
    password: str


class AppletPassword(InternalModel):
    password: str
