import datetime
import uuid

from fastapi import Query
from pydantic import Field

from apps.shared.domain import InternalModel

__all__ = ["EventQueryParams", "ScheduleEventsExportParams"]

from apps.shared.query_params import QueryParams


class EventQueryParams(InternalModel):
    respondent_id: uuid.UUID | None


class ScheduleEventsExportParams(QueryParams):
    respondent_ids: list[uuid.UUID] | None = Field(Query(None))
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
    limit: int = 10000
