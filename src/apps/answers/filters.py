import datetime
import uuid

from fastapi import Query
from pydantic import Field, root_validator

from apps.shared.query_params import BaseQueryParams


class SummaryActivityFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None
    target_subject_id: uuid.UUID | None


class AppletActivityFilter(BaseQueryParams):
    target_subject_id: uuid.UUID | None
    created_date: datetime.date


class AppletActivityAnswerFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None
    from_datetime: datetime.datetime | None
    to_datetime: datetime.datetime | None
    identifiers: str | None = None
    versions: list[str] | None
    empty_identifiers: bool = True
    target_subject_id: uuid.UUID | None


class AppletSubmitDateFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None
    target_subject_id: uuid.UUID | None
    from_date: datetime.date
    to_date: datetime.date

    @classmethod
    @root_validator
    def check_both_fields_not_none(cls, values):
        respondent_id = values.get("respondent_id")
        target_subject_id = values.get("target_subject_id")
        if respondent_id is None and target_subject_id is None:
            raise ValueError("At least one of fields be provided")
        return values


class AnswerExportFilters(BaseQueryParams):
    respondent_ids: list[uuid.UUID] | None = Field(Query(None))
    target_subject_ids: list[uuid.UUID] | None = Field(Query(None))
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
    limit: int = 10000


class AnswerIdentifierVersionFilter(BaseQueryParams):
    from_datetime: datetime.datetime | None
    to_datetime: datetime.datetime | None
