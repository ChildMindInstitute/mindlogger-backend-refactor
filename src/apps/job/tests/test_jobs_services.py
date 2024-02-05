import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.job.constants import JobStatus
from apps.job.crud import JobCRUD
from apps.job.db.schemas import JobSchema
from apps.job.service import JobService
from apps.users.db.schemas import UserSchema


@pytest.mark.parametrize("status,", (JobStatus.in_progress, JobStatus.pending, JobStatus.retry))
async def test_job_is_in_progress(job: JobSchema, session: AsyncSession, status: JobStatus) -> None:
    await JobCRUD(session).update(job.id, status=status)
    srv = JobService(session, job.creator_id)
    in_progress = await srv.is_job_in_progress(job.name)
    assert in_progress


@pytest.mark.parametrize("status,", (JobStatus.success, JobStatus.error))
async def test_job_is_not_in_progress(job: JobSchema, session: AsyncSession, status: JobStatus) -> None:
    await JobCRUD(session).update(job.id, status=status)
    srv = JobService(session, job.creator_id)
    in_progress = await srv.is_job_in_progress(job.name)
    assert not in_progress


async def test_job_does_not_exist(job: JobSchema, session: AsyncSession) -> None:
    srv = JobService(session, job.creator_id)
    in_progress = await srv.is_job_in_progress("doesnotexist")
    assert not in_progress


@pytest.mark.parametrize("status,", list(JobStatus))
async def test_change_status_with_details(
    job: JobSchema,
    session: AsyncSession,
    status: JobStatus,
    job_details: dict[str, str],
) -> None:
    assert not job.details
    srv = JobService(session, job.creator_id)
    job_updated = await srv.change_status(job.id, status, details=job_details)
    assert job_updated.status == status
    assert job_updated.details == job_details


async def test_change_status_without_details(
    job: JobSchema,
    session: AsyncSession,
) -> None:
    assert job.status != JobStatus.success
    srv = JobService(session, job.creator_id)
    job_updated = await srv.change_status(job.id, JobStatus.success)
    assert job_updated.status == JobStatus.success


async def test_get_or_create_owned__create_job_default_status_is_pending(
    session: AsyncSession, tom: UserSchema
) -> None:
    job_name = "tomjob"
    srv = JobService(session, tom.id)
    job = await srv.get_or_create_owned(job_name)
    assert job.status == JobStatus.pending
    assert job.creator_id == tom.id
    assert job.name == job_name


async def test_get_or_create_owned__create_job_with_status_in_progress(session: AsyncSession, tom: UserSchema) -> None:
    job_name = "tomjob"
    srv = JobService(session, tom.id)
    job = await srv.get_or_create_owned(job_name, status=JobStatus.in_progress)
    assert job.status == JobStatus.in_progress


async def test_get_or_create_owned__create_job_with_details(
    session: AsyncSession,
    tom: UserSchema,
    job_details: dict[str, str],
) -> None:
    job_name = "tomjob"
    srv = JobService(session, tom.id)
    job = await srv.get_or_create_owned(job_name, details=job_details)
    assert job.details == job_details


async def test_get_or_create_owned__get_existing_job(session: AsyncSession, job: JobSchema) -> None:
    srv = JobService(session, job.creator_id)
    j = await srv.get_or_create_owned(job.name)
    assert j.id == job.id
