import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import Field

from apps.shared.domain import InternalModel


class EHRData(InternalModel):
    date: datetime
    healthcare_provider_id: str | None = None
    healthcare_provider_name: str | None = None
    resources: list[dict] = Field(default_factory=list)
    submit_id: uuid.UUID
    activity_id: uuid.UUID
    target_subject_id: uuid.UUID
    user_id: uuid.UUID


class EHRFileTypeEnum(StrEnum):
    DOCS = "DOCS"
    EHR = "EHR"


class EHRFileMetadata(InternalModel):
    name: str
    size: int
    type: EHRFileTypeEnum


class EHRMetadata(InternalModel):
    zip_files: list[EHRFileMetadata]
    storage_path: str
