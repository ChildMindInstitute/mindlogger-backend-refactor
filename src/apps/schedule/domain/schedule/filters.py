import uuid
from typing import Annotated

from fastapi import Query
from pydantic import Field

from apps.shared.domain import InternalModel

__all__ = ["EventQueryParams", "ScheduleEventsExportParams"]

from apps.shared.query_params import BaseQueryParams
from config import settings


class EventQueryParams(InternalModel):
    respondent_id: uuid.UUID | None = None


class ScheduleEventsExportParams(BaseQueryParams):
    activity_or_flow_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    respondent_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    subject_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    limit: Annotated[int, Field(gt=0, le=settings.service.result_limit)] = settings.service.result_limit
