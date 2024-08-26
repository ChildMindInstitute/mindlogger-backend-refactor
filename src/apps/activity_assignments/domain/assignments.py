from uuid import UUID

from pydantic import BaseModel, root_validator

from apps.activity_assignments.errors import ActivityAssignmentActivityOrFlowError, ActivityAssignmentNotActivityAndFlowError, ActivityAssignmentMissingRespondentError, ActivityAssignmentMissingTargetError
from apps.shared.domain import InternalModel, PublicModel
from apps.subjects.domain import SubjectReadResponse


class ActivityAssignmentCreate(BaseModel):
    activity_id: UUID | None
    activity_flow_id: UUID | None
    respondent_subject_id: UUID
    target_subject_id: UUID

    @root_validator
    def validate_assignments(cls, values):
        if not values.get("activity_id") and not values.get("activity_flow_id"):
            raise ActivityAssignmentActivityOrFlowError()

        if values.get("activity_id") and values.get("activity_flow_id"):
            raise ActivityAssignmentActivityOrFlowError("Only one of activity_id or activity_flow_id must be provided")

        return values


class ActivitiesAssignmentsCreate(InternalModel):
    assignments: list[ActivityAssignmentCreate]


class ActivityAssignment(PublicModel):
    id: UUID
    activity_flow_id: UUID | None
    activity_id: UUID | None
    respondent_subject_id: UUID
    target_subject_id: UUID


class ActivitiesAssignments(PublicModel):
    applet_id: UUID
    assignments: list[ActivityAssignment]


class ActivityAssignmentsListQueryParams(InternalModel):
    activities: str | None
    flows: str | None


class ActivityAssignmentWithSubject(PublicModel):
    activity_flow_id: UUID | None
    activity_id: UUID | None
    respondent_subject: SubjectReadResponse
    target_subject: SubjectReadResponse


class ActivitiesAssignmentsWithSubjects(PublicModel):
    applet_id: UUID
    assignments: list[ActivityAssignmentWithSubject]

class ActivityAssignmentDelete(BaseModel):
    activity_id: UUID | None
    activity_flow_id: UUID | None
    respondent_subject_id: UUID
    target_subject_id: UUID

    @root_validator
    def validate_assignments(cls, values):
        # Validate that exactly one of activity_id or activity_flow_id is provided
        if not values.get("activity_id") and not values.get("activity_flow_id"):
            raise ActivityAssignmentNotActivityAndFlowError()

        # Validate that respondent_subject_id is provided
        if not values.get("respondent_subject_id"):
            raise ActivityAssignmentMissingRespondentError()

        # Validate that target_subject_id is provided
        if not values.get("target_subject_id"):
            raise ActivityAssignmentMissingTargetError()

        # Ensure that only one of activity_id or activity_flow_id is provided
        if values.get("activity_id") and values.get("activity_flow_id"):
            raise ActivityAssignmentActivityOrFlowError()

        return values


class ActivitiesAssignmentsDelete(InternalModel):
    assignments: list[ActivityAssignmentDelete]
