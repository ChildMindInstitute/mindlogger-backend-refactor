import uuid
from datetime import datetime

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
