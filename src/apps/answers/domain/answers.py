import datetime
import enum
import uuid
from copy import deepcopy
from typing import Annotated, Any, Generic, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from apps.activities.domain.activity_full import ActivityFull, PublicActivityItemFull
from apps.activities.domain.activity_history import (
    ActivityHistoryExport,
    ActivityHistoryFull,
    ActivityHistoryTranslatedExport,
)
from apps.activities.domain.response_type_config import ResponseType
from apps.activities.domain.scores_reports import SubscaleSetting
from apps.activity_flows.domain.flow_full import FlowFull, FlowHistoryWithActivityFlat, FlowHistoryWithActivityFull
from apps.answers.domain.answer_items import AnswerItem, ItemAnswerCreate
from apps.applets.domain.base import AppletBaseInfo
from apps.integrations.oneup_health.service.domain import EHRMetadata
from apps.integrations.prolific.domain import ProlificParamsActivityAnswer
from apps.shared.domain import InternalModel, PublicModel, Response
from apps.shared.domain.custom_validations import datetime_from_ms
from apps.shared.domain.types import TruncatedInt, _BaseModel
from apps.shared.locale import I18N
from apps.subjects.domain import SubjectReadResponse
from infrastructure.database.mixins import HistoryAware


class ClientMeta(InternalModel):
    app_id: str
    app_version: str
    width: TruncatedInt | None = None
    height: TruncatedInt | None = None


class Answer(InternalModel):
    id: uuid.UUID
    applet_id: uuid.UUID
    version: str
    submit_id: uuid.UUID
    client: ClientMeta | None = None
    applet_history_id: str
    flow_history_id: str | None = None
    activity_history_id: str
    respondent_id: uuid.UUID | None = None
    is_flow_completed: bool | None = False
    target_subject_id: uuid.UUID | None = None
    source_subject_id: uuid.UUID | None = None
    input_subject_id: uuid.UUID | None = None
    relation: str | None = None

    migrated_data: dict | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    migrated_date: datetime.datetime | None = None
    migrated_updated: datetime.datetime | None = None
    is_deleted: bool

    answer_item: AnswerItem


class ParagraphText(InternalModel):
    value: str
    should_identify_response: bool = False


class Text(InternalModel):
    value: str
    should_identify_response: bool = False


class SingleSelection(InternalModel):
    value: uuid.UUID
    additional_text: str | None = None


class MultipleSelection(InternalModel):
    value: list[uuid.UUID]
    additional_text: str | None = None


class Slider(InternalModel):
    value: float
    additional_text: str | None = None


AnswerTypes = SingleSelection | Slider | MultipleSelection | Text | ParagraphText

ANSWER_TYPE_MAP: dict[ResponseType, Any] = {
    ResponseType.TEXT: Text,
    ResponseType.PARAGRAPHTEXT: ParagraphText,
    ResponseType.SINGLESELECT: SingleSelection,
    ResponseType.MULTISELECT: MultipleSelection,
    ResponseType.SLIDER: Slider,
}


class AnswerAlert(InternalModel):
    activity_item_id: uuid.UUID
    message: str


class AppletAnswerCreate(InternalModel):
    applet_id: uuid.UUID
    version: str
    submit_id: uuid.UUID
    flow_id: uuid.UUID | None = None
    is_flow_completed: bool | None = None
    activity_id: uuid.UUID
    answer: ItemAnswerCreate
    created_at: datetime.datetime | None = None
    alerts: Annotated[list[AnswerAlert], Field(default_factory=list)]
    client: ClientMeta
    target_subject_id: uuid.UUID | None = None
    source_subject_id: uuid.UUID | None = None
    input_subject_id: uuid.UUID | None = None
    consent_to_share: bool | None = False
    prolific_params: ProlificParamsActivityAnswer | None = None
    event_history_id: str | None = None
    allowed_ehr_ingest: bool | None = False

    _dates_from_ms = field_validator("created_at", mode="before")(datetime_from_ms)


class AssessmentAnswerCreate(InternalModel):
    answer: str
    item_ids: list[uuid.UUID]
    reviewer_public_key: str
    assessment_version_id: str
    reviewed_flow_submit_id: uuid.UUID | None = None


class AnswerDate(InternalModel):
    created_at: datetime.datetime
    answer_id: uuid.UUID
    end_datetime: datetime.datetime


class ReviewActivity(InternalModel):
    id: uuid.UUID
    name: str
    answer_dates: Annotated[list[AnswerDate], Field(default_factory=list)]


class SummaryActivityFlow(InternalModel):
    id: uuid.UUID
    name: str
    has_answer: bool
    last_answer_date: datetime.datetime | None = None


class SummaryActivity(SummaryActivityFlow):
    is_performance_task: bool


class PublicAnswerDate(PublicModel):
    created_at: datetime.datetime
    answer_id: uuid.UUID
    end_datetime: datetime.datetime


class ReviewItem(PublicModel, BaseModel, Generic[_BaseModel]):
    id: uuid.UUID
    name: str
    answer_dates: Annotated[list[_BaseModel], Field(default_factory=list)]


class PublicReviewActivity(ReviewItem[PublicAnswerDate]):
    last_answer_date: Annotated[datetime.datetime | None, Field(validate_default=True)] = None

    @field_validator("last_answer_date")
    @classmethod
    def calculate_last_answer_date(
        cls, value: datetime.datetime | None, info: ValidationInfo
    ) -> datetime.datetime | None:
        answer_dates = info.data.get("answer_dates", [])
        if answer_dates:
            value = max(v.created_at for v in answer_dates)
        return value


class SubmissionDate(PublicModel):
    submit_id: uuid.UUID
    created_at: datetime.datetime
    end_datetime: datetime.datetime


class ReviewFlow(ReviewItem[SubmissionDate]): ...


class PublicReviewFlow(ReviewFlow):
    last_answer_date: Annotated[datetime.datetime | None, Field(validate_default=True)] = None

    @field_validator("last_answer_date")
    @classmethod
    def calculate_last_answer_date(
        cls, value: datetime.datetime | None, info: ValidationInfo
    ) -> datetime.datetime | None:
        answer_dates = info.data.get("answer_dates", [])
        if answer_dates:
            value = max(v.created_at for v in answer_dates)
        return value


class FlowSubmissionInfo(PublicModel):
    submit_id: uuid.UUID
    flow_history_id: str
    applet_id: uuid.UUID
    version: str
    created_at: datetime.datetime
    end_datetime: datetime.datetime


class PublicSummaryActivityFlow(InternalModel):
    id: uuid.UUID
    name: str
    has_answer: bool
    last_answer_date: datetime.datetime | None = None


class PublicSummaryActivity(PublicSummaryActivityFlow):
    is_performance_task: bool


class PublicAnswerDates(PublicModel):
    dates: list[datetime.date]


class IdentifierData(InternalModel):
    identifier: str
    user_public_key: str
    is_encrypted: bool
    last_answer_date: datetime.datetime


class Identifier(InternalModel):
    identifier: str
    user_public_key: str | None = None
    last_answer_date: datetime.datetime


class ActivityAnswer(PublicModel):
    id: uuid.UUID
    submit_id: uuid.UUID
    version: str
    activity_history_id: str
    activity_id: Annotated[uuid.UUID | None, Field(validate_default=True)] = None
    flow_history_id: str | None = None
    user_public_key: str | None = None
    answer: str | None = None
    events: str | None = None
    item_ids: Annotated[list[str], Field(default_factory=list)]
    identifier: str | None = None
    migrated_data: dict | None = None
    end_datetime: datetime.datetime
    created_at: datetime.datetime
    source_subject: SubjectReadResponse | None = None

    @field_validator("activity_id")
    @classmethod
    def extract_activity_id(cls, value, info: ValidationInfo):
        if val := info.data.get("activity_history_id"):
            return val[:36]


class SubmissionSummary(PublicModel):
    end_datetime: datetime.datetime
    created_at: datetime.datetime
    identifier: Identifier | None = None
    version: str


class ActivitySubmission(PublicModel):
    activity: ActivityHistoryFull
    answer: ActivityAnswer


class ActivitySubmissionResponse(ActivitySubmission):
    summary: Annotated[SubmissionSummary | None, Field(validate_default=True)] = None

    @field_validator("summary")
    @classmethod
    def generate_summary(cls, value, info: ValidationInfo) -> list[Any]:
        if not value:
            answer: ActivityAnswer = info.data["answer"]
            if answer:
                value = SubmissionSummary(
                    end_datetime=answer.end_datetime,
                    created_at=answer.created_at,
                    version=answer.version,
                )
                if answer.identifier:
                    if answer.migrated_data and answer.migrated_data.get("is_identifier_encrypted") is False:
                        value.identifier = Identifier(identifier=answer.identifier, last_answer_date=answer.created_at)
                    else:
                        value.identifier = Identifier(
                            identifier=answer.identifier,
                            last_answer_date=answer.created_at,
                            user_public_key=answer.user_public_key,
                        )
        return value


class ReviewsCount(PublicModel):
    mine: int = 0
    other: int = 0


class AppletSubmission(PublicModel):
    applet_id: uuid.UUID
    respondent_subject_id: uuid.UUID
    respondent_subject_tag: str | None = None
    respondent_secret_user_id: str | None = None
    respondent_nickname: str | None = None
    target_subject_id: uuid.UUID
    target_subject_tag: str | None = None
    target_secret_user_id: str | None = None
    target_nickname: str | None = None
    source_subject_id: uuid.UUID | None = None
    source_subject_tag: str | None = None
    source_secret_user_id: str | None = None
    source_nickname: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    activity_name: str
    activity_id: uuid.UUID


class FlowSubmission(PublicModel):
    submit_id: uuid.UUID
    flow_history_id: str
    applet_id: uuid.UUID
    version: str
    created_at: datetime.datetime
    end_datetime: datetime.datetime | None = None
    is_completed: bool | None = None
    answers: list[ActivityAnswer]
    review_count: ReviewsCount = ReviewsCount()


class FlowSubmissionsDetails(PublicModel):
    submissions: list[FlowSubmission]
    flows: list[FlowHistoryWithActivityFull]


class FlowSubmissionsResponse(PublicModel):
    submissions: list[FlowSubmission]
    flows: list[FlowHistoryWithActivityFlat]

    @field_validator("flows", mode="before")
    @classmethod
    def format_flows(cls, value):
        if value:
            if isinstance(value[0], dict) and "items" in value[0]:
                _values = []
                for _value in value:
                    data = deepcopy(_value)
                    del data["items"]
                    data["activities"] = [item["activity"] for item in _value["items"]]
                    _values.append(data)
                value = _values
            elif isinstance(value[0], FlowHistoryWithActivityFull):
                _values = []
                for _value in value:
                    data = _value.model_dump(exclude={"items"})
                    data["activities"] = [item.activity for item in _value.items]
                    _values.append(data)
                value = _values

        return value


class PublicFlowSubmissionsResponse(Response[FlowSubmissionsResponse]):
    count: int = 0


class FlowSubmissionDetails(PublicModel):
    submission: FlowSubmission
    flow: FlowHistoryWithActivityFull


class FlowSubmissionResponse(PublicModel):
    submission: FlowSubmission
    flow: FlowHistoryWithActivityFlat
    summary: Annotated[SubmissionSummary | None, Field(validate_default=True)] = None

    @field_validator("flow", mode="before")
    @classmethod
    def format_flow(cls, value):
        if isinstance(value, dict) and "items" in value:
            data = deepcopy(value)
            del data["items"]
            data["activities"] = [item["activity"] for item in value["items"]]
            value = data
        elif isinstance(value, FlowHistoryWithActivityFull):
            data = value.model_dump(exclude={"items"})
            data["activities"] = [item.activity for item in value.items]
            value = data

        return value

    @field_validator("summary")
    @classmethod
    def generate_summary(cls, value, info: ValidationInfo) -> list[Any]:
        if not value:
            answers: list[ActivityAnswer] = info.data["submission"].answers
            if answers:
                value = SubmissionSummary(
                    end_datetime=answers[0].end_datetime,
                    created_at=answers[0].created_at,
                    version=answers[0].version,
                )
                for answer in answers:
                    if identifier := answer.identifier:
                        if answer.migrated_data and answer.migrated_data.get("is_identifier_encrypted") is False:
                            value.identifier = Identifier(identifier=identifier, last_answer_date=answer.created_at)
                        else:
                            value.identifier = Identifier(
                                identifier=identifier,
                                last_answer_date=answer.created_at,
                                user_public_key=answer.user_public_key,
                            )
                        break

        return value


class AppletActivityAnswer(InternalModel):
    answer_id: uuid.UUID
    version: str | None = None
    user_public_key: str | None = None
    answer: str | None = None
    events: str | None = None
    item_ids: Annotated[list[str], Field(default_factory=list)]
    items: Annotated[list[PublicActivityItemFull], Field(default_factory=list)]
    start_datetime: datetime.datetime | None = None
    end_datetime: datetime.datetime | None = None
    subscale_setting: SubscaleSetting | None = None


class AssessmentAnswer(InternalModel):
    reviewer_public_key: str | None = None
    answer: str | None = None
    item_ids: Annotated[list[str], Field(default_factory=list)]
    items: Annotated[list[PublicActivityItemFull], Field(default_factory=list)]
    items_last: Annotated[list[PublicActivityItemFull] | None, Field(default_factory=list)]
    is_edited: bool = False
    versions: list[str] = []


class Reviewer(InternalModel):
    id: uuid.UUID
    first_name: str
    last_name: str


class AnswerReview(InternalModel):
    id: uuid.UUID
    reviewer_public_key: str | None = None
    answer: str | None = None
    item_ids: Annotated[list[str], Field(default_factory=list)]
    items: Annotated[list[PublicActivityItemFull], Field(default_factory=list)]
    reviewer: Reviewer
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AppletActivityAnswerPublic(PublicModel):
    answer_id: uuid.UUID
    version: str
    user_public_key: str | None = None
    answer: str | None = None
    events: str | None = None
    item_ids: Annotated[list[str], Field(default_factory=list)]
    items: Annotated[list[PublicActivityItemFull], Field(default_factory=list)]
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    subscale_setting: SubscaleSetting | None = None
    review_count: ReviewsCount


class ReviewerPublic(PublicModel):
    id: uuid.UUID
    first_name: str
    last_name: str


class AnswerReviewPublic(PublicModel):
    id: uuid.UUID
    reviewer_public_key: str | None = None
    answer: str | None = None
    item_ids: Annotated[list[str], Field(default_factory=list)]
    items: Annotated[list[PublicActivityItemFull], Field(default_factory=list)]
    reviewer: ReviewerPublic
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AssessmentAnswerPublic(PublicModel):
    reviewer_public_key: str | None = None
    answer: str | None = None
    item_ids: Annotated[list[str], Field(default_factory=list)]
    items: Annotated[list[PublicActivityItemFull], Field(default_factory=list)]
    items_last: Annotated[list[PublicActivityItemFull] | None, Field(default_factory=list)]
    versions: list[str]


class AnswerNote(InternalModel):
    note: str


class NoteOwner(InternalModel):
    id: uuid.UUID
    first_name: str
    last_name: str


class AnswerNoteDetail(InternalModel):
    id: uuid.UUID
    user: NoteOwner
    note: str
    created_at: datetime.datetime


class NoteOwnerPublic(PublicModel):
    id: uuid.UUID
    first_name: str
    last_name: str


class AnswerNoteDetailPublic(PublicModel):
    id: uuid.UUID
    user: NoteOwnerPublic
    note: str
    created_at: datetime.datetime


class UserAnswerDataBase(BaseModel):
    id: uuid.UUID
    submit_id: uuid.UUID
    version: str
    respondent_id: uuid.UUID | str | None = None
    respondent_secret_id: str | None = None
    source_subject_id: uuid.UUID | str | None = None
    source_secret_id: uuid.UUID | str | None = None
    source_user_nickname: str | None = None
    source_user_tag: str | None = None
    target_subject_id: uuid.UUID | str | None = None
    target_secret_id: uuid.UUID | str | None = None
    target_user_nickname: str | None = None
    target_user_tag: str | None = None
    input_subject_id: uuid.UUID | str | None = None
    input_secret_id: uuid.UUID | str | None = None
    input_user_nickname: str | None = None
    relation: str | None = None
    legacy_profile_id: str | None = None
    user_public_key: str | None = None
    answer: str | None = None
    item_ids: Annotated[list[str], Field(default_factory=list)]
    events: str | None = None
    scheduled_datetime: datetime.datetime | None = None
    start_datetime: datetime.datetime | None = None
    end_datetime: datetime.datetime | None = None
    migrated_date: datetime.datetime | None = None
    tz_offset: int | None = None
    scheduled_event_id: uuid.UUID | str | None = None
    scheduled_event_history_id: str | None = None
    applet_history_id: str
    activity_history_id: str | None = None
    flow_history_id: str | None = None
    flow_name: str | None = None
    reviewed_answer_id: uuid.UUID | str | None = None
    reviewed_flow_submit_id: uuid.UUID | str | None = None
    created_at: datetime.datetime
    migrated_data: dict | None = None
    client: ClientMeta | None = None
    ehr_data_file: str | None = None


class RespondentAnswerData(UserAnswerDataBase, InternalModel):
    is_manager: bool = False
    respondent_email: str | None = None


class RespondentAnswerDataPublic(UserAnswerDataBase, PublicModel):
    applet_id: Annotated[str | None, Field(validate_default=True)] = None
    activity_id: Annotated[str | None, Field(validate_default=True)] = None
    flow_id: Annotated[str | None, Field(validate_default=True)] = None

    @field_validator("applet_id")
    @classmethod
    def extract_applet_id(cls, value, info: ValidationInfo):
        return info.data["applet_history_id"][:36]

    @field_validator("activity_id")
    @classmethod
    def extract_activity_id(cls, value, info: ValidationInfo):
        if val := info.data.get("activity_history_id"):
            return val[:36]

    @field_validator("flow_id")
    @classmethod
    def extract_flow_id(cls, value, info: ValidationInfo):
        if val := info.data.get("flow_history_id"):
            return val[:36]

    @field_validator("start_datetime", "end_datetime", "scheduled_datetime")
    @classmethod
    def convert_to_timestamp(cls, value: datetime.datetime):
        if value:
            return value.replace(tzinfo=datetime.timezone.utc).timestamp()
        return None


class AnswerExport(InternalModel):
    answers: Annotated[list[RespondentAnswerData], Field(default_factory=list)]
    activities: Annotated[list[ActivityHistoryFull], Field(default_factory=list)]
    total_answers: int = 0


class PublicAnswerExportTranslated(PublicModel):
    answers: Annotated[list[RespondentAnswerDataPublic], Field(default_factory=list)]
    activities: Annotated[list[ActivityHistoryTranslatedExport], Field(default_factory=list)]


class PublicAnswerExport(PublicModel):
    answers: Annotated[list[RespondentAnswerDataPublic], Field(default_factory=list)]
    activities: Annotated[list[ActivityHistoryExport], Field(default_factory=list)]

    def translate(self, i18n: I18N) -> PublicAnswerExportTranslated:
        return PublicAnswerExportTranslated(
            answers=self.answers,
            activities=[activity.translate(i18n) for activity in self.activities],
        )


class PublicAnswerExportResponse(Response[PublicAnswerExportTranslated]):
    count: int = 0


class SafeApplet(AppletBaseInfo, InternalModel):
    id: uuid.UUID
    version: str
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None

    activities: Annotated[list[ActivityFull], Field(default_factory=list)]
    activity_flows: Annotated[list[FlowFull], Field(default_factory=list)]


class ReportServerEmail(InternalModel):
    body: str
    subject: str
    attachment: str
    email_recipients: list[str]


class ReportServerResponse(InternalModel):
    pdf: str
    email: ReportServerEmail


class CompletedEntity(PublicModel):
    id: uuid.UUID = Field(
        deprecated=True,
        description="Deprecated: id is the unversioned activity_id or flow_id. "
        "Use versioned activity_history_id and flow_history_id instead.",
    )
    answer_id: uuid.UUID
    submit_id: uuid.UUID
    activity_history_id: str | None = Field(None, exclude=True)
    flow_history_id: str | None = Field(None, exclude=True)
    target_subject_id: uuid.UUID | None = None
    scheduled_event_id: str | None = None
    local_end_date: datetime.date
    local_end_time: datetime.time
    start_time: datetime.time | None = None
    end_time: datetime.time | None = None
    is_flow_completed: bool | None = None
    activity_flow_order: int | None = Field(
        default=None,
        description="1-indexed position of the activity within the flow, from flow_item_histories.order. "
        "None for standalone activities (not part of a flow).",
    )

    @field_validator("id", mode="before")
    @classmethod
    def id_from_history_id(cls, value):
        return HistoryAware().id_from_history_id(value)

    @property
    def activity_id(self) -> uuid.UUID | None:
        """Deprecated: Use versioned activity_history_id instead."""
        return HistoryAware().id_from_history_id(self.activity_history_id)

    @property
    def flow_id(self) -> uuid.UUID | None:
        """Deprecated: Use versioned flow_history_id instead."""
        return HistoryAware().id_from_history_id(self.flow_history_id)

    @property
    def group_progress_id(self) -> tuple[uuid.UUID | None, str | None, uuid.UUID | None, uuid.UUID]:
        """Mimics groupProgressId in client.

        This should be deprecated in the future if we support versioning more fully on the client.
        """
        return (self.flow_id or self.activity_id, self.scheduled_event_id, self.target_subject_id, self.submit_id)

    @property
    def group_progress_history_id(self) -> tuple[str | None, str | None, uuid.UUID | None, uuid.UUID]:
        """Similar to groupProgressId in client, except with versioned IDs.

        Also mirrors the DISTINCT clause in SQL queries for:

            AnswersCRUD.get_completed_answers_data
            AnswersCRUD.get_completed_answers_data_list

        We use this as the natural key for grouping activities in flows in:

            AnswerService.get_completed_answers_data
            AnswerService.get_completed_answers_data_list

        """
        return (
            self.flow_history_id or self.activity_history_id,
            self.scheduled_event_id,
            self.target_subject_id,
            self.submit_id,
        )


class AppletCompletedEntities(InternalModel):
    id: uuid.UUID
    version: Optional[str] = None

    activities: list[CompletedEntity]
    activity_flows: list[CompletedEntity]


class AnswersCheck(PublicModel):
    applet_id: uuid.UUID
    # Used to distinguish between duplicate activities in flows
    created_at: int | None = None
    activity_id: str
    submit_id: uuid.UUID | None = None


class AnswerExistenceResponse(PublicModel):
    exists: bool


class ArbitraryPreprocessor(PublicModel):
    applet_id: uuid.UUID | None = None


class IdentifiersQueryParams(InternalModel):
    respondent_id: uuid.UUID | None = None
    target_subject_id: uuid.UUID | None = None
    answer_id: uuid.UUID | None = None


class MultiinformantAssessmentValidationResponse(PublicModel):
    valid: bool
    message: str | None = None
    code: str | None = None


class PublicSubmissionsResponse(PublicModel):
    submissions: Annotated[list[AppletSubmission], Field(default_factory=list)]
    submissions_count: int = 0
    participants_count: int = 0


class AnswersCopyCheckResult(InternalModel):
    total_answers: int
    not_copied_answers: set[uuid.UUID]
    answers_to_remove: set[uuid.UUID]
    total_answer_items: int
    not_copied_answer_items: set[uuid.UUID]


class FilesCopyCheckResult(InternalModel):
    total_files: int
    not_copied_files: set[str]
    files_to_remove: set[str]


class SubmissionsSubjectCounters(InternalModel):
    respondents: Annotated[set[uuid.UUID], Field(default_factory=set)]
    subjects: Annotated[set[uuid.UUID], Field(default_factory=set)]
    subject_submissions_count: int = 0
    subject_last_submission_date: datetime.datetime | None = None
    respondent_submissions_count: int = 0
    respondent_last_submission_date: datetime.datetime | None = None


class SubmissionsActivityMetadataBySubject(InternalModel):
    subject_id: uuid.UUID
    activities: Annotated[dict[uuid.UUID, SubmissionsSubjectCounters], Field(default_factory=dict)]


class EHRIngestionStatus(enum.StrEnum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"


class AnswerEHR(InternalModel):
    submit_id: uuid.UUID
    ehr_ingestion_status: EHRIngestionStatus
    activity_id: uuid.UUID
    ehr_storage_uri: str | None = None
    meta: EHRMetadata | None = None


class AnswerEHRFull(AnswerEHR):
    target_subject_id: uuid.UUID
    date: datetime.datetime
