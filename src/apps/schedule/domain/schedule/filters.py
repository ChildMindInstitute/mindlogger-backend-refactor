import datetime
import uuid

from fastapi import Query
from pydantic import Field

from apps.shared.domain import InternalModel

__all__ = ["EventQueryParams", "ScheduleEventsExportParams"]

from apps.shared.query_params import BaseQueryParams
from config import settings


class EventQueryParams(InternalModel):
    respondent_id: uuid.UUID | None


class ScheduleEventsExportParams(BaseQueryParams):
    respondent_ids: list[uuid.UUID] | None = Field(Query(None))
    subject_ids: list[uuid.UUID] | None = Field(Query(None))
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
    limit: int = Field(gt=0, default=settings.service.result_limit, le=settings.service.result_limit)
