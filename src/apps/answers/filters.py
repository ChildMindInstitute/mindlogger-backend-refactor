import datetime
import uuid
from typing import Self

from fastapi import Query
from pydantic import Field, model_validator, validator

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

    @model_validator(mode="after")
    def check_both_fields_not_none(self) -> Self:
        respondent_id = values.respondent_id
        target_subject_id = values.target_subject_id
        if respondent_id is None and target_subject_id is None:
            raise ValueError("At least one of fields be provided")
        return self


class AnswerExportFilters(BaseQueryParams):
    respondent_ids: list[uuid.UUID] | None = Field(Query(None))
    target_subject_ids: list[uuid.UUID] | None = Field(Query(None))
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
    limit: int = 10000
    include_ehr: bool = False


class AnswerIdentifierVersionFilter(BaseQueryParams):
    from_datetime: datetime.datetime | None
    to_datetime: datetime.datetime | None


class AppletMultiinformantAssessmentParams(InternalModel):
    target_subject_id: uuid.UUID
    source_subject_id: uuid.UUID
    activity_or_flow_id: uuid.UUID


class AnswerEHRExportFilters(BaseQueryParams):
    respondent_ids: list[uuid.UUID] | None = Field(Query(None))
    target_subject_ids: list[uuid.UUID] | None = Field(Query(None))
    activity_ids: list[uuid.UUID] | None = Field(Query(None))
    flow_ids: list[uuid.UUID] | None = Field(Query(None))
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
