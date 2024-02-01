import datetime
import uuid

from apps.job.constants import JobStatus
from apps.shared.domain import InternalModel


class JobCreate(InternalModel):
    name: str
    creator_id: uuid.UUID
    status: JobStatus
    details: dict | None = None


class Job(JobCreate):
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
