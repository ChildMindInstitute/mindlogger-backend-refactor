import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.job.constants import JobStatus
from apps.job.crud import JobCRUD
from apps.job.db.schemas import JobSchema
from apps.job.domain import JobCreate


async def test_create_job_with_details(session: AsyncSession, job_create: JobCreate, job_details: dict[str, str]):
    assert not job_create.details
    job_create.details = job_details
    crud = JobCRUD(session)
    job = await crud.create(job_create)
    assert job.details == job_create.details


async def test_update_job_name(job: JobSchema, session: AsyncSession):
    newname = job.name + "new"
    crud = JobCRUD(session)
    job_updated = await crud.update(job.id, name=newname)
    assert job_updated.name == newname


async def test_update_job_status(job: JobSchema, session: AsyncSession):
    assert job.status == JobStatus.in_progress
    crud = JobCRUD(session)
    job_updated = await crud.update(job.id, status=JobStatus.error)
    assert job_updated.status == JobStatus.error


async def test_get_job_by_name(job: JobSchema, session: AsyncSession):
    crud = JobCRUD(session)
    j = await crud.get_by_name(job.name, job.creator_id)
    assert j
    assert j.id == job.id


async def test_get_job_by_name__job_does_not_exist_with_name(job: JobSchema, session: AsyncSession):
    crud = JobCRUD(session)
    j = await crud.get_by_name(job.name + "notexists", job.creator_id)
    assert j is None


async def test_get_job_by_name__job_does_not_exist_with_creator_id(
    job: JobSchema, session: AsyncSession, uuid_zero: uuid.UUID
):
    crud = JobCRUD(session)
    j = await crud.get_by_name(job.name, uuid_zero)
    assert j is None
