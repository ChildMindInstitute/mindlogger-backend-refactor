import datetime
import uuid

from fastapi import Query
from pydantic import Field, validator

from apps.shared.domain.custom_validations import array_from_string
from apps.shared.query_params import BaseQueryParams


class SummaryActivityFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None


class ReviewAppletItemFilter(BaseQueryParams):
    respondent_id: uuid.UUID
    created_date: datetime.date


class AppletSubmissionsFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None
    from_datetime: datetime.datetime | None
    to_datetime: datetime.datetime | None
    identifiers: list[str] | None = Field(Query(None))
    versions: list[str] | None = Field(Query(None))
    empty_identifiers: bool = True

    _parse_array = validator("versions", "identifiers", pre=True, allow_reuse=True)(array_from_string(True))


class AppletSubmitDateFilter(BaseQueryParams):
    respondent_id: uuid.UUID
    from_date: datetime.date
    to_date: datetime.date


class AnswerExportFilters(BaseQueryParams):
    respondent_ids: list[uuid.UUID] | None = Field(Query(None))
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
    limit: int = 10000


class AnswerIdentifierVersionFilter(BaseQueryParams):
    from_datetime: datetime.datetime | None
    to_datetime: datetime.datetime | None
