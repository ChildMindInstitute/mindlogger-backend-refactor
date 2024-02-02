from typing import Any, AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.job.constants import JobStatus
from apps.job.crud import JobCRUD
from apps.job.db.schemas import JobSchema
from apps.job.domain import JobCreate


@pytest.fixture
def job_create(user_tom) -> JobCreate:
    return JobCreate(
        name="test",
        creator_id=user_tom.id,
        status=JobStatus.in_progress,
        details=None,
    )


@pytest.fixture()
async def job(session: AsyncSession, job_create: JobCreate) -> AsyncGenerator[JobSchema, Any]:
    job = await JobCRUD(session).create(job_create)
    yield JobSchema(**job.dict())


@pytest.mark.parametrize("status,", list(JobStatus))
async def test_create_job(
    session: AsyncSession,
    status: JobStatus,
    job_create: JobCreate,
) -> None:
    crud = JobCRUD(session)
    job_create.status = status
    job = await crud.create(job_create)
    assert job.name == job_create.name
    assert job.creator_id == job_create.creator_id
    assert job.status == status
    assert not job.details


@pytest.fixture
def job_details() -> dict[str, str]:
    return {"key": "val"}
