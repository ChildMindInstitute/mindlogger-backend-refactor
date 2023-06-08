import datetime
import uuid

from fastapi import Query
from pydantic import Field

from apps.shared.query_params import BaseQueryParams


class AppletActivityFilter(BaseQueryParams):
    respondent_id: uuid.UUID
    created_date: datetime.date


class AppletSubmitDateFilter(BaseQueryParams):
    respondent_id: uuid.UUID
    from_date: datetime.date
    to_date: datetime.date


class AnswerExportFilters(BaseQueryParams):
    respondent_ids: list[uuid.UUID] | None = Field(Query(None))


class AnswerIdentifierVersionFilter(BaseQueryParams):
    from_datetime: datetime.datetime | None
    to_datetime: datetime.datetime | None
