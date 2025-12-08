import uuid

from sqlalchemy import select, update

from apps.job.db.schemas import JobSchema
from apps.job.domain import Job, JobCreate
from infrastructure.database import BaseCRUD


class JobCRUD(BaseCRUD[JobSchema]):
    schema_class = JobSchema

    async def get_by_name(self, name: str, user_id: uuid.UUID) -> Job | None:
        query = (
            select(JobSchema)
            .where(
                JobSchema.creator_id == user_id,
                JobSchema.name == name,
            )
            .order_by(JobSchema.name.desc())
        )
        results = await self._execute(query=query)

        schema = results.scalars().one_or_none()
        if not schema:
            return None
        return Job.model_validate(schema)

    async def create(self, model: JobCreate) -> Job:
        schema = await self._create(JobSchema(**model.model_dump(by_alias=False, exclude_unset=True)))
        return Job.model_validate(schema)

    async def update(self, id_: uuid.UUID, **data) -> Job:
        query = update(JobSchema).where(JobSchema.id == id_).values(**data).returning(JobSchema)

        db_result = await self._execute(query)
        job_schema = db_result.first()

        return Job.model_validate(job_schema)
