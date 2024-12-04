import uuid
from datetime import datetime
from enum import Enum

from pydantic import Field

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item import (
    ActivityItemDuplicate,
    ActivityItemSingleLanguageDetail,
    ActivityItemSingleLanguageDetailPublic,
)
from apps.activities.domain.response_type_config import PerformanceTaskType, ResponseType
from apps.activities.domain.scores_reports import ScoresAndReports
from apps.activity_assignments.domain.assignments import ActivityAssignmentWithSubject
from apps.shared.domain import InternalModel, PublicModel


class ActivityOrFlowStatusEnum(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    HIDDEN = "hidden"
    DELETED = "deleted"


class ActivityOrFlowBasicInfoPublic(PublicModel):
    id: uuid.UUID
    name: str
    description: str
    images: list[str] = Field(default_factory=list)
    is_flow: bool = False
    status: ActivityOrFlowStatusEnum
    auto_assign: bool = True
    activity_ids: list[uuid.UUID] | None = None
    performance_task_type: PerformanceTaskType | None = None
    is_performance_task: bool | None = None


class ActivityOrFlowBasicInfoInternal(InternalModel):
    id: uuid.UUID
    name: str
    description: str
    images: list[str] = Field(default_factory=list)
    is_flow: bool = False
    status: ActivityOrFlowStatusEnum | None
    auto_assign: bool = True
    is_hidden: bool = False
    activity_ids: list[uuid.UUID] | None = None
    performance_task_type: PerformanceTaskType | None = None
    is_performance_task: bool | None = None

    def set_status(self, assignments: list[ActivityAssignmentWithSubject], include_auto: bool):
        """
        Determine and set the value of the status field
        """
        if self.is_hidden:
            self.status = ActivityOrFlowStatusEnum.HIDDEN
        elif assignments or (include_auto and self.auto_assign):
            self.status = ActivityOrFlowStatusEnum.ACTIVE
        else:
            self.status = ActivityOrFlowStatusEnum.INACTIVE


class Activity(ActivityBase, InternalModel):
    id: uuid.UUID
    order: int


class ActivityDuplicate(ActivityBase, InternalModel):
    id: uuid.UUID
    key: uuid.UUID
    order: int
    items: list[ActivityItemDuplicate] = Field(default_factory=list)


class ActivityPublic(ActivityBase, InternalModel):
    id: uuid.UUID
    order: int


class ActivitySingleLanguageDetail(ActivityBase, InternalModel):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    created_at: datetime


class ActivitySingleLanguageDetailPublic(ActivityBase, PublicModel):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    created_at: datetime


class ActivityMinimumInfo(InternalModel):
    id: uuid.UUID
    name: str
    description: str
    image: str = ""
    is_hidden: bool | None = False
    order: int


class ActivitySingleLanguageMobileDetailPublic(ActivityMinimumInfo, InternalModel):
    is_reviewable: bool = False
    is_skippable: bool = False
    show_all_at_once: bool = False
    response_is_editable: bool = False
    splash_screen: str = ""


class ActivitySingleLanguageWithItemsDetail(ActivityBase, InternalModel):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    items: list[ActivityItemSingleLanguageDetail] = Field(default_factory=list)
    created_at: datetime


class ActivitySingleLanguageWithItemsDetailPublic(ActivityBase, PublicModel):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    items: list[ActivityItemSingleLanguageDetailPublic] = Field(default_factory=list)
    created_at: datetime


class ActivityLanguageWithItemsMobileDetailPublic(PublicModel):
    id: uuid.UUID
    name: str
    description: str
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    is_hidden: bool | None = False
    response_is_editable: bool = False
    order: int
    items: list[ActivityItemSingleLanguageDetailPublic] = Field(default_factory=list)
    scores_and_reports: ScoresAndReports | None = None
    performance_task_type: PerformanceTaskType | None = None
    is_performance_task: bool = False
    auto_assign: bool | None = True


class ActivityWithAssignmentDetailsPublic(ActivityLanguageWithItemsMobileDetailPublic):
    assignments: list[ActivityAssignmentWithSubject] = Field(default_factory=list)


class ActivityOrFlowWithAssignmentsPublic(ActivityOrFlowBasicInfoPublic):
    assignments: list[ActivityAssignmentWithSubject] = Field(default_factory=list)


class ActivityBaseInfo(ActivityMinimumInfo, InternalModel):
    contains_response_types: list[ResponseType]
    item_count: int
    auto_assign: bool


class ActivitySubjectCounters(PublicModel):
    activity_or_flow_id: uuid.UUID
    respondents_count: int
    respondent_submissions_count: int
    subjects_count: int
    subject_submissions_count: int


class ActivitiesCounters(PublicModel):
    subject_id: uuid.UUID
    respondent_activities_count: int = 0
    target_activities_count: int = 0
    activities_or_flows: list[ActivitySubjectCounters] = Field(default_factory=list)
