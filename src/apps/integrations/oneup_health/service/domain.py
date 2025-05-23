import uuid
from datetime import datetime

from apps.shared.domain import InternalModel


class EHRData(InternalModel):
    date: datetime
    healthcare_provider_id: str
    resources: list[dict]
    submit_id: uuid.UUID
    activity_id: uuid.UUID
