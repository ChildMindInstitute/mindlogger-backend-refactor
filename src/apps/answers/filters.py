import datetime
import uuid
from typing import Annotated, Self

from fastapi import Query
from pydantic import Field, field_validator, model_validator

from apps.shared.domain.base import InternalModel
from apps.shared.domain.custom_validations import array_from_string
from apps.shared.domain.types import TruncatedDate
from apps.shared.query_params import BaseQueryParams


class SummaryActivityFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None = None
    target_subject_id: uuid.UUID | None = None


class ReviewAppletItemFilter(BaseQueryParams):
    target_subject_id: uuid.UUID
    created_date: TruncatedDate


class AppletSubmissionsFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None = None
    from_datetime: datetime.datetime | None = None
    to_datetime: datetime.datetime | None = None
    identifiers: str | None = None
    versions: str | None = None
    empty_identifiers: bool = True
    target_subject_id: uuid.UUID | None = None

    _parse_array = field_validator("versions", "identifiers")(array_from_string(True))


class AppletSubmitDateFilter(BaseQueryParams):
    respondent_id: uuid.UUID | None = None
    target_subject_id: uuid.UUID | None = None
    from_date: TruncatedDate
    to_date: TruncatedDate
    activity_or_flow_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def check_both_fields_not_none(self) -> Self:
        respondent_id = self.respondent_id
        target_subject_id = self.target_subject_id
        if respondent_id is None and target_subject_id is None:
            raise ValueError("At least one of fields be provided")
        return self


class AnswerExportFilters(BaseQueryParams):
    respondent_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    target_subject_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
    limit: int = 10000
    include_ehr: bool = False


class AnswerIdentifierVersionFilter(BaseQueryParams):
    from_datetime: datetime.datetime | None = None
    to_datetime: datetime.datetime | None = None


class AppletMultiinformantAssessmentParams(InternalModel):
    target_subject_id: uuid.UUID
    source_subject_id: uuid.UUID
    activity_or_flow_id: uuid.UUID


class AnswerEHRExportFilters(BaseQueryParams):
    respondent_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    target_subject_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    activity_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    flow_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
