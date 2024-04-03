import datetime
import uuid

from pydantic import validator

from apps.shared.domain.base import InternalModel
from apps.shared.domain.custom_validations import datetime_from_ms


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


class AnswerItem(InternalModel):
    answer_id: uuid.UUID
    respondent_id: uuid.UUID
    is_assessment: bool
    assessment_activity_id: str | None


class ItemAnswerCreate(InternalModel):
    answer: str | None
    events: str | None
    item_ids: list[uuid.UUID]
    identifier: str | None
    scheduled_time: datetime.datetime | None
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
