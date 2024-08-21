from typing import Any

from pydantic import Field, root_validator

from apps.activities.domain.activity_create import ActivityCreate
from apps.activities.domain.activity_update import ActivityUpdate
from apps.activities.domain.custom_validation import validate_performance_task_type
from apps.activities.errors import (
    AssessmentLimitExceed,
    DuplicateActivityFlowNameError,
    DuplicateActivityNameError,
    DuplicatedActivitiesError,
    DuplicatedActivityFlowsError,
    FlowItemActivityKeyNotFoundError,
)
from apps.activity_flows.domain.flow_create import FlowCreate
from apps.activity_flows.domain.flow_update import FlowUpdate
from apps.applets.domain.base import AppletBase, AppletReportConfigurationBase, Encryption
from apps.shared.domain import InternalModel, PublicModel


class AppletCreate(AppletReportConfigurationBase, AppletBase, InternalModel):
    activities: list[ActivityCreate]
    activity_flows: list[FlowCreate]
    extra_fields: dict = Field(default_factory=dict)

    @root_validator()
    def validate_existing_ids_for_duplicate(cls, values) -> list[Any]:
        activities: list[ActivityCreate] = values.get("activities", [])
        flows: list[FlowCreate] = values.get("activity_flows", [])

        activity_names = set()
        activity_keys = set()
        flow_names = set()
        assessments_count = 0
        for activity in activities:
            if activity.name in activity_names:
                raise DuplicateActivityNameError()
            activity_names.add(activity.name)
            activity_keys.add(activity.key)
            assessments_count += int(activity.is_reviewable)

        if assessments_count > 1:
            raise AssessmentLimitExceed()

        for flow in flows:
            if flow.name in flow_names:
                raise DuplicateActivityFlowNameError()
            flow_names.add(flow.name)
            for flow_item in flow.items:
                if flow_item.activity_key not in activity_keys:
                    raise FlowItemActivityKeyNotFoundError()
        return values

    @root_validator
    def validate_performance_task_type(cls, values):
        return validate_performance_task_type(values)


class AppletUpdate(AppletBase, PublicModel):
    activities: list[ActivityUpdate]
    activity_flows: list[FlowUpdate]

    @root_validator()
    def validate_existing_ids_for_duplicate(cls, values) -> list[Any]:
        activities: list[ActivityUpdate] = values.get("activities", [])
        flows: list[FlowUpdate] = values.get("activity_flows", [])

        activity_names = set()
        activity_keys = set()

        flow_names = set()
        activity_ids = set()
        flow_ids = set()
        assessments_count = 0
        for activity in activities:
            if activity.name in activity_names:
                raise DuplicateActivityNameError()
            if activity.id and activity.id in activity_ids:
                raise DuplicatedActivitiesError()
            activity_ids.add(activity.id)
            activity_names.add(activity.name)
            activity_keys.add(activity.key)

            assessments_count += int(activity.is_reviewable)

        if assessments_count > 1:
            raise AssessmentLimitExceed()

        for flow in flows:
            if flow.name in flow_names:
                raise DuplicateActivityFlowNameError()
            if flow.id and flow.id in flow_ids:
                raise DuplicatedActivityFlowsError()
            for flow_item in flow.items:
                if flow_item.activity_key not in activity_keys:
                    raise FlowItemActivityKeyNotFoundError()

            flow_ids.add(flow.id)
            flow_names.add(flow.name)
        return values


class AppletReportConfiguration(AppletReportConfigurationBase, InternalModel):
    pass


class AppletDuplicateRequest(InternalModel):
    display_name: str
    encryption: Encryption
