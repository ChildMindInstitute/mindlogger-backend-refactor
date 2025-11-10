from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from apps.activity_assignments.errors import (
    ActivityAssignmentActivityOrFlowError,
    ActivityAssignmentNotActivityAndFlowError,
)
from apps.shared.domain import InternalModel, PublicModel
from apps.subjects.domain import SubjectReadResponse


def _validate_assignments(activity_id: UUID | None, activity_flow_id: UUID | None) -> None:
    if not activity_id and not activity_flow_id:
        raise ActivityAssignmentNotActivityAndFlowError()
    if activity_id and activity_flow_id:
        raise ActivityAssignmentActivityOrFlowError("Only one of activity_id or activity_flow_id must be provided")


class ActivityAssignmentCreate(BaseModel):
    activity_id: UUID | None = None
    activity_flow_id: UUID | None = None
    respondent_subject_id: UUID
    target_subject_id: UUID

    @model_validator(mode="after")
    def validate_assignments(self) -> Self:
        _validate_assignments(self.activity_id, self.activity_flow_id)
        return self


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
    id: UUID
    activity_flow_id: UUID | None
    activity_id: UUID | None
    respondent_subject: SubjectReadResponse
    target_subject: SubjectReadResponse


class ActivitiesAssignmentsWithSubjects(PublicModel):
    applet_id: UUID
    assignments: list[ActivityAssignmentWithSubject]


class ActivityAssignmentDelete(BaseModel):
    activity_id: UUID | None = None
    activity_flow_id: UUID | None = None
    respondent_subject_id: UUID
    target_subject_id: UUID

    @model_validator(mode="after")
    def validate_assignments(self) -> Self:
        _validate_assignments(self.activity_id, self.activity_flow_id)
        return self


class ActivitiesAssignmentsDelete(InternalModel):
    assignments: list[ActivityAssignmentDelete]


class AssignmentsSubjectCounters(PublicModel):
    respondents: set[UUID] = Field(default_factory=set)
    subjects: set[UUID] = Field(default_factory=set)
    subject_assignments_count: int = 0
    respondent_assignments_count: int = 0


class AssignmentsActivityCountBySubject(PublicModel):
    subject_id: UUID
    activities: dict[UUID, AssignmentsSubjectCounters] = Field(default_factory=dict)
