import uuid
from typing import Any

from apps.job.constants import JobStatus
from apps.job.crud import JobCRUD
from apps.job.domain import Job, JobCreate


class JobService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session

    async def get_or_create_owned(
        self,
        name: str,
        status: JobStatus = JobStatus.pending,
        details: dict | None = None,
    ) -> Job:
        repository = JobCRUD(self.session)
        job = await repository.get_by_name(name, self.user_id)
        if not job:
            model = JobCreate(
                name=name,
                creator_id=self.user_id,
                status=status,
            )
            if details:
                model.details = details
            job = await repository.create(model)

        return job

    async def is_job_in_progress(self, job_name: str) -> bool:
        repository = JobCRUD(self.session)
        job = await repository.get_by_name(job_name, self.user_id)
        if not job or job.status in [JobStatus.success, JobStatus.error]:
            return False

        return True

    async def change_status(
        self, id_: uuid.UUID, status: JobStatus, details: dict | None = None
    ) -> Job:
        data: dict[str, Any] = dict(status=status)
        if details:
            data["details"] = details
        return await JobCRUD(self.session).update(id_, **data)
