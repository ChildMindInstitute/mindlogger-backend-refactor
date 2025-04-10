import random
import uuid
from datetime import datetime, timezone

from apps.integrations.oneup_health.service.oneup_health import OneupHealthService
from apps.subjects.domain import Subject
from apps.subjects.services import SubjectsService
from broker import broker
from config import settings
from infrastructure.database import session_manager
from infrastructure.logger import logger

__all__ = ["task_ingest_user_data"]


def _exponential_backoff(retry_count) -> int:
    """
    Calculate exponential backoff time for retries with optional jitter.

    Implements exponential backoff algorithm: base_delay * 2^retry_count
    with an optional jitter to prevent thundering herd problem.

    Args:
        retry_count (int): Current retry attempt (0-based)

    Returns:
        int: Time to wait in seconds (between 0.75x-1.25x of calculated delay)
    """
    base_delay = settings.oneup_health.base_backoff_delay
    max_delay = settings.oneup_health.max_backoff_delay

    # Calculate exponential delay with upper bound
    delay = min(base_delay * (2**retry_count), max_delay)
    if delay == max_delay:
        return 0

    jitter_multiplier = 0.75 + random.random() * 0.5  # Random value between 0.75 and 1.25
    delay *= jitter_multiplier

    # Convert to integer
    return int(delay)


async def _process_data_transfer(session, subject: Subject, start_date: datetime) -> bool:
    """
    Process the OneUp Health data transfer for a subject.

    Args:
        session: Database session
        subject (Subject): The subject whose data is being retrieved
        start_date (datetime): The start date of the transfer process

    Returns:
        bool: True if the data transfer is complete, False otherwise
    """
    oneup_health_service = OneupHealthService()
    oneup_user_id = subject.meta.get("oneup_user_id") if subject.meta else None
    if oneup_user_id is None:
        return False

    # Check if transfer is completed or timed out
    initiated_count = await oneup_health_service.check_for_transfer_initiated(oneup_user_id, start_date)
    if initiated_count > 0:
        logger.info(f"Transfer initiated for subject {subject.id}")
        completed_count = await oneup_health_service.check_for_transfer_completed(oneup_user_id, start_date)
        timeout_count = await oneup_health_service.check_for_transfer_timeout(oneup_user_id, start_date)

        if completed_count + timeout_count == initiated_count:
            logger.info(f"Transfer {'completed' if completed_count > 0 else 'timed out'} for subject {subject.id}")
            return await oneup_health_service.get_patient_data(session, subject)

    return False


async def _schedule_retry(subject_id: uuid.UUID, start_date: datetime, retry_count: int) -> None:
    """
    Schedule a retry of the data ingestion task with exponential backoff.

    Args:
        subject_id (uuid.UUID): The ID of the subject whose data is being retrieved
        start_date (datetime): The start date of the transfer process
        retry_count (int): The current retry attempt count
    """
    delay = _exponential_backoff(retry_count)
    if delay > 0:
        retry_count += 1
        logger.info(f"Scheduling retry #{retry_count} in {delay} seconds")
        await (
            task_ingest_user_data.kicker()
            .with_labels(delay=delay)
            .kiq(subject_id=subject_id, start_date=start_date, retry_count=retry_count)
        )


@broker.task
async def task_ingest_user_data(subject_id: uuid.UUID, start_date: datetime | None = None, retry_count: int = 0):
    """
    Asynchronous task to ingest user health data from OneUp Health.

    This task polls for data transfer status and retrieves patient data when ready.
    If the transfer is not complete, it reschedules itself with exponential backoff.

    Args:
        subject_id (uuid.UUID): The ID of the subject whose data is being retrieved
        start_date (datetime, optional): The start date of the transfer process
        retry_count (int): The current retry attempt count

    Returns:
        list | None: List of retrieved resources if successful, None otherwise
    """
    # Initialize start date if not provided
    start_date = start_date or datetime.now(timezone.utc)

    try:
        # Get subject and check for OneUp Health integration
        async with session_manager.get_session()() as session:
            subject = await SubjectsService(session, uuid.uuid4()).exist_by_id(subject_id)

            # Validate OneUp Health user ID exists
            oneup_user_id = subject.meta.get("oneup_user_id") if subject.meta else None
            if oneup_user_id is None:
                logger.info(f"Subject {subject_id} has no OneUp Health user ID")
                return

            # Process data transfer
            if await _process_data_transfer(session, subject, start_date) is False:
                logger.info(f"Data transfer not complete for subject {subject_id}")
                await _schedule_retry(subject_id, start_date, retry_count)
                return

    except Exception as e:
        logger.error(f"Error in task_ingest_user_data: {str(e)}")
        return
