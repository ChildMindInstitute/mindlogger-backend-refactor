import datetime
import uuid

from fastapi import Query
from pydantic import Field

from apps.shared.query_params import BaseQueryParams


class SummaryActivityFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None


class AppletActivityFilter(BaseQueryParams):
    respondent_id: uuid.UUID
    created_date: datetime.date


class AppletActivityAnswerFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None
    from_datetime: datetime.datetime | None
    to_datetime: datetime.datetime | None
    identifiers: str | None = ""
    versions: str | None
    empty_identifiers: bool = False


class AppletSubmitDateFilter(BaseQueryParams):
    respondent_id: uuid.UUID
    from_date: datetime.date
    to_date: datetime.date


class AnswerExportFilters(BaseQueryParams):
    respondent_ids: list[uuid.UUID] | None = Field(Query(None))
    from_date: datetime.date | None = None
    limit: int | None = 10000


class AnswerIdentifierVersionFilter(BaseQueryParams):
    from_datetime: datetime.datetime | None
    to_datetime: datetime.datetime | None
