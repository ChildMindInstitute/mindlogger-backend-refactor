import datetime
import uuid
from typing import Any

from pydantic import BaseModel, Field, validator

from apps.activities.domain.activity_full import PublicActivityItemFull
from apps.activities.domain.activity_history import (
    ActivityHistoryExport,
    ActivityHistoryFull,
)
from apps.activities.domain.response_type_config import ResponseType
from apps.shared.domain import InternalModel, PublicModel


class Text(InternalModel):
    value: str
    should_identify_response: bool = False


class SingleSelection(InternalModel):
    value: uuid.UUID
    additional_text: str | None


class MultipleSelection(InternalModel):
    value: list[uuid.UUID]
    additional_text: str | None


class Slider(InternalModel):
    value: float
    additional_text: str | None


AnswerTypes = SingleSelection | Slider | MultipleSelection | Text

ANSWER_TYPE_MAP: dict[ResponseType, Any] = {
    ResponseType.TEXT: Text,
    ResponseType.SINGLESELECT: SingleSelection,
    ResponseType.MULTISELECT: MultipleSelection,
    ResponseType.SLIDER: Slider,
}


class ActivityItemAnswerCreate(InternalModel):
    flow_id: uuid.UUID | None = None
    activity_id: uuid.UUID
    answer: str
    events: str | None
    item_ids: list[uuid.UUID]

    @validator("item_ids")
    def convert_item_ids(cls, value: list[uuid.UUID]):
        return list(map(str, value))


class AnswerItemSchemaAnsweredActivityItem(InternalModel):
    activity_item_history_id: str
    answer: str


class AppletAnswerCreate(InternalModel):
    applet_id: uuid.UUID
    version: str
    answers: list[ActivityItemAnswerCreate]
    created_at: int | None
    user_public_key: str

    @validator("answers")
    def validate_answers(cls, value: list[ActivityItemAnswerCreate]):
        answer_activity_ids = set()
        for answer in value:
            if answer.activity_id in answer_activity_ids:
                raise ValueError("Duplicate activity")
            answer_activity_ids.add(answer.activity_id)
        return value


class AssessmentAnswerCreate(InternalModel):
    activity_id: uuid.UUID
    answer: str
    item_ids: list[uuid.UUID]
    reviewer_public_key: str


class AnswerDate(InternalModel):
    created_at: datetime.datetime
    answer_id: uuid.UUID


class AnsweredAppletActivity(InternalModel):
    id: uuid.UUID
    name: str
    answer_dates: list[AnswerDate] = Field(default_factory=list)


class PublicAnswerDate(PublicModel):
    created_at: datetime.datetime
    answer_id: uuid.UUID


class PublicAnsweredAppletActivity(PublicModel):
    id: uuid.UUID
    name: str
    answer_dates: list[PublicAnswerDate] = Field(default_factory=list)


class PublicAnswerDates(PublicModel):
    dates: list[datetime.date]


class ActivityAnswer(InternalModel):
    user_public_key: str | None
    answer: str | None
    events: str | None
    item_ids: list[str] = Field(default_factory=list)
    items: list[PublicActivityItemFull] = Field(default_factory=list)


class AssessmentAnswer(InternalModel):
    reviewer_public_key: str | None
    answer: str | None
    item_ids: list[str] = Field(default_factory=list)
    items: list[PublicActivityItemFull] = Field(default_factory=list)
    is_edited: bool = False


class Reviewer(InternalModel):
    first_name: str
    last_name: str


class AnswerReview(InternalModel):
    reviewer_public_key: str | None
    answer: str | None
    item_ids: list[str] = Field(default_factory=list)
    items: list[PublicActivityItemFull] = Field(default_factory=list)
    is_edited: bool = False
    reviewer: Reviewer


class ActivityAnswerPublic(PublicModel):
    user_public_key: str | None
    answer: str | None
    events: str | None
    item_ids: list[str] = Field(default_factory=list)
    items: list[PublicActivityItemFull] = Field(default_factory=list)


class ReviewerPublic(PublicModel):
    first_name: str
    last_name: str


class AnswerReviewPublic(PublicModel):
    reviewer_public_key: str | None
    answer: str | None
    item_ids: list[str] = Field(default_factory=list)
    items: list[PublicActivityItemFull] = Field(default_factory=list)
    is_edited: bool = False
    reviewer: ReviewerPublic


class AssessmentAnswerPublic(PublicModel):
    reviewer_public_key: str | None
    answer: str | None
    item_ids: list[str] = Field(default_factory=list)
    items: list[PublicActivityItemFull] = Field(default_factory=list)
    is_edited: bool = False


class AnswerNote(InternalModel):
    note: str


class NoteOwner(InternalModel):
    first_name: str
    last_name: str


class AnswerNoteDetail(InternalModel):
    id: uuid.UUID
    user: NoteOwner
    note: str
    created_at: datetime.datetime


class NoteOwnerPublic(PublicModel):
    first_name: str
    last_name: str


class AnswerNoteDetailPublic(PublicModel):
    id: uuid.UUID
    user: NoteOwnerPublic
    note: str
    created_at: datetime.datetime


class UserAnswerDataBase(BaseModel):
    id: uuid.UUID
    version: str
    user_public_key: str | None
    answer: str | None = None
    item_ids: list[str] = Field(default_factory=list)
    applet_history_id: str
    activity_history_id: str
    created_at: datetime.datetime


class RespondentAnswerDataBase(UserAnswerDataBase):
    respondent_id: uuid.UUID | str | None = None
    respondent_secret_id: str | None = None
    events: str | None = None
    flow_history_id: str | None
    flow_name: str | None
    reviewed_answer_id: uuid.UUID | str | None


class RespondentAnswerData(RespondentAnswerDataBase, InternalModel):
    is_manager: bool = False
    respondent_email: str | None = None


class RespondentAnswerDataPublic(RespondentAnswerDataBase, PublicModel):
    applet_id: str | None
    activity_id: str | None
    flow_id: str | None

    @validator("applet_id", always=True)
    def extract_applet_id(cls, value, values):
        return values["applet_history_id"][:36]

    @validator("activity_id", always=True)
    def extract_activity_id(cls, value, values):
        return values["activity_history_id"][:36]

    @validator("flow_id", always=True)
    def extract_flow_id(cls, value, values):
        if val := values.get("flow_history_id"):
            return val[:36]

        return value


class AnswerExport(InternalModel):
    answers: list[RespondentAnswerData] = Field(default_factory=list)
    activities: list[ActivityHistoryFull] = Field(default_factory=list)


class PublicAnswerExport(PublicModel):
    answers: list[RespondentAnswerDataPublic] = Field(default_factory=list)
    activities: list[ActivityHistoryExport] = Field(default_factory=list)
