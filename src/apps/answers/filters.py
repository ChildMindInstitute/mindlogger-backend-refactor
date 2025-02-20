import datetime
import uuid

from fastapi import Query
from pydantic import Field, root_validator, validator

from apps.shared.domain.base import InternalModel
from apps.shared.domain.custom_validations import array_from_string
from apps.shared.query_params import BaseQueryParams


class SummaryActivityFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None
    target_subject_id: uuid.UUID | None


class ReviewAppletItemFilter(BaseQueryParams):
    target_subject_id: uuid.UUID
    created_date: datetime.date


class AppletSubmissionsFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None
    from_datetime: datetime.datetime | None
    to_datetime: datetime.datetime | None
    identifiers: str | None
    versions: str | None
    empty_identifiers: bool = True
    target_subject_id: uuid.UUID | None

    _parse_array = validator("versions", "identifiers", allow_reuse=True)(array_from_string(True))


class AppletSubmitDateFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None
    target_subject_id: uuid.UUID | None
    from_date: datetime.date
    to_date: datetime.date
    activity_or_flow_id: uuid.UUID | None = None

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


class AppletMultiinformantAssessmentParams(InternalModel):
    target_subject_id: uuid.UUID
    source_subject_id: uuid.UUID
    activity_or_flow_id: uuid.UUID
