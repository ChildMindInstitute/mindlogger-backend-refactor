import datetime
import uuid

from pydantic import validator

from apps.shared.domain.base import InternalModel
from apps.shared.domain.custom_validations import datetime_from_ms


class AnswerItem(InternalModel):
    id: uuid.UUID
    answer_id: uuid.UUID
    respondent_id: uuid.UUID
    answer: str | None
    events: str | None
    item_ids: list
    identifier: str | None
    user_public_key: str | None
    scheduled_datetime: datetime.datetime | None = None
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    scheduled_event_id: str | None = None
    local_end_date: datetime.date | None = None
    local_end_time: datetime.time | None = None
    migrated_data: dict | None = None
    is_assessment: bool = False
    assessment_activity_id: str | None = None
    tz_offset: int | None = None

    created_at: datetime.datetime
    updated_at: datetime.datetime
    migrated_date: datetime.datetime | None = None
    migrated_updated: datetime.datetime | None = None
    is_deleted: bool


class AnswerItemSchemaAnsweredActivityItem(InternalModel):
    activity_item_history_id: str
    answer: str


class AnswerItemDataEncrypted(InternalModel):
    id: uuid.UUID
    answer: str
    events: str | None
    identifier: str | None


class UserAnswerItemData(AnswerItemDataEncrypted):
    user_public_key: str
    migrated_data: dict | None


class AssessmentItem(InternalModel):
    answer_id: uuid.UUID
    respondent_id: uuid.UUID
    is_assessment: bool
    assessment_activity_id: str | None


class ItemAnswerCreate(InternalModel):
    answer: str | None = None
    events: str | None = None
    item_ids: list[uuid.UUID]
    identifier: str | None = None
    scheduled_time: datetime.datetime | None = None
    start_time: datetime.datetime
    end_time: datetime.datetime
    user_public_key: str | None
    scheduled_event_id: str | None = None
    local_end_date: datetime.date | None = None
    local_end_time: datetime.time | None = None
    tz_offset: int | None = None

    @validator("item_ids")
    def convert_item_ids(cls, value: list[uuid.UUID]):
        return list(map(str, value))

    _dates_from_ms = validator("start_time", "end_time", "scheduled_time", pre=True, allow_reuse=True)(datetime_from_ms)
