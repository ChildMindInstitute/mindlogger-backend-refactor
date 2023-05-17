from pydantic import root_validator

from apps.activities.domain.activity_create import ActivityCreate
from apps.activities.domain.activity_update import ActivityUpdate
from apps.activities.errors import (
    DuplicateActivityFlowNameError,
    DuplicateActivityNameError,
    DuplicatedActivitiesError,
    DuplicatedActivityFlowsError,
)
from apps.activity_flows.domain.flow_create import FlowCreate
from apps.activity_flows.domain.flow_update import FlowUpdate
from apps.applets.domain.base import (
    AppletBase,
    AppletReportConfigurationBase,
    Encryption,
)
from apps.shared.domain import InternalModel


class AppletCreate(AppletReportConfigurationBase, AppletBase, InternalModel):
    activities: list[ActivityCreate]
    activity_flows: list[FlowCreate]

    @root_validator()
    def validate_existing_ids_for_duplicate(cls, values):
        activities = values.get("activities", [])
        flows = values.get("activity_flows", [])

        activity_names = set()
        flow_names = set()
        for activity in activities:  # type:ActivityCreate
            if activity.name in activity_names:
                raise DuplicateActivityNameError()
            activity_names.add(activity.name)

        for flow in flows:  # type:FlowCreate
            if flow.name in flow_names:
                raise DuplicateActivityFlowNameError()
            flow_names.add(flow.name)
        return values


class AppletUpdate(AppletBase, InternalModel):
    activities: list[ActivityUpdate]
    activity_flows: list[FlowUpdate]

    @root_validator()
    def validate_existing_ids_for_duplicate(cls, values):
        activities = values.get("activities", [])
        flows = values.get("activity_flows", [])

        activity_names = set()
        flow_names = set()
        activity_ids = set()
        flow_ids = set()
        for activity in activities:  # type:ActivityUpdate
            if activity.name in activity_names:
                raise DuplicateActivityNameError()
            if activity.id and activity.id in activity_ids:
                raise DuplicatedActivitiesError()
            activity_ids.add(activity.id)
            activity_names.add(activity.name)

        for flow in flows:  # type:FlowUpdate
            if flow.name in flow_names:
                raise DuplicateActivityFlowNameError()
            if flow.id and flow.id in flow_ids:
                raise DuplicatedActivityFlowsError()
            flow_ids.add(flow.id)
            flow_names.add(flow.name)
        return values


class AppletReportConfiguration(AppletReportConfigurationBase, InternalModel):
    pass


class AppletDuplicateRequest(InternalModel):
    display_name: str
    encryption: Encryption
