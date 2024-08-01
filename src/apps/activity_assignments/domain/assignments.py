from uuid import UUID

from pydantic import BaseModel, root_validator

from apps.activity_assignments.errors import (
    ActivityAssignmentActivityOrFlowError,
    ActivityAssignmentRespondentOrInvitationError,
)
from apps.shared.domain import InternalModel, PublicModel


class ActivityAssignmentCreate(BaseModel):
    activity_id: UUID | None
    activity_flow_id: UUID | None
    respondent_id: UUID | None
    target_subject_id: UUID | None
    invitation_id: UUID | None

    @root_validator
    def validate_assignments(cls, values):
        if not values.get("activity_id") and not values.get("activity_flow_id"):
            raise ActivityAssignmentActivityOrFlowError()

        if not values.get("respondent_id") and not values.get("invitation_id"):
            raise ActivityAssignmentRespondentOrInvitationError()

        return values


class ActivitiesAssignmentsCreate(InternalModel):
    assignments: list[ActivityAssignmentCreate]


class ActivityAssignment(PublicModel):
    id: UUID
    activity_flow_id: UUID | None
    activity_id: UUID | None
    respondent_id: UUID | None
    target_subject_id: UUID | None
    invitation_id: UUID | None


class ActivitiesAssignments(PublicModel):
    applet_id: UUID
    assignments: list[ActivityAssignment]
