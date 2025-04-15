import random
import uuid
from datetime import datetime

import httpx

from apps.integrations.oneup_health.service.oneup_health import OneupHealthService
from apps.shared.exception import BaseError
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


async def _process_data_transfer(
    session, applet_id: uuid.UUID, unique_id: uuid.UUID, oneup_user_id: int, start_date: datetime | None
) -> bool:
    """
    Process the OneUp Health data transfer for a subject.

    Args:
        session: Database session
        applet_id (uuid.UUID): The unique identifier for the applet
        unique_id (uuid.UUID): The unique identifier for the user
        oneup_user_id (int): The OneUp Health user ID
        start_date (datetime): The start date of the transfer process

    Returns:
        bool: True if the data transfer is complete, False otherwise
    """
    oneup_health_service = OneupHealthService()

    # Check if transfer is completed or timed out
    initiated_count = await oneup_health_service.check_for_transfer_initiated(oneup_user_id, start_date)
    if initiated_count > 0:
        logger.info(f"Transfer initiated for OneUp Health user ID {oneup_user_id} ({initiated_count} transfers)")
        completed_count = await oneup_health_service.check_for_transfer_completed(oneup_user_id, start_date)
        timeout_count = await oneup_health_service.check_for_transfer_timeout(oneup_user_id, start_date)

        if completed_count + timeout_count == initiated_count:
            logger.info(
                f"Transfer {'completed' if completed_count > 0 else 'timed out'} "
                f"for OneUp Health user ID {oneup_user_id}"
            )
            try:
                return await oneup_health_service.get_patient_data(session, applet_id, unique_id, oneup_user_id)
            except httpx.RequestError as e:
                logger.error(f"Failed to get patient data for OneUp Health user ID {oneup_user_id}")
                logger.exception(f"Error: {e}")
                return False

    return False


async def _schedule_retry(
    applet_id: uuid.UUID, unique_id: uuid.UUID, start_date: datetime | None, retry_count: int
) -> None:
    """
    Schedule a retry of the data ingestion task with exponential backoff.

    Args:
        applet_id (uuid.UUID): The unique identifier for the applet
        unique_id (uuid.UUID): The unique identifier for the user
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
            .kiq(applet_id=applet_id, unique_id=unique_id, start_date=start_date, retry_count=retry_count)
        )


@broker.task
async def task_ingest_user_data(
    applet_id: uuid.UUID, unique_id: uuid.UUID, start_date: datetime | None = None, retry_count: int = 0
):
    """
    Asynchronous task to ingest user health data from OneUp Health.

    This task polls for data transfer status and retrieves patient data when ready.
    If the transfer is not complete, it reschedules itself with exponential backoff.

    Args:
        applet_id (uuid.UUID): The unique identifier for the applet
        unique_id (uuid.UUID): The unique identifier for the user
        start_date (datetime, optional): The start date of the transfer process
        retry_count (int): The current retry attempt count

    Returns:
        list | None: List of retrieved resources if successful, None otherwise
    """

    try:
        # Get subject and check for OneUp Health integration
        async with session_manager.get_session()() as session:
            oneup_user_id = await OneupHealthService().get_oneup_user_id(unique_id=unique_id)
            if oneup_user_id is None:
                logger.info(f"ID {unique_id} has no OneUp Health user ID")
                return

            # Process data transfer
            if await _process_data_transfer(session, applet_id, unique_id, oneup_user_id, start_date) is False:
                logger.info(f"Data transfer not complete for OneUp Health user ID {oneup_user_id}")
                await _schedule_retry(applet_id, unique_id, start_date, retry_count)
                return

    except BaseError as e:
        logger.error(f"Error in task_ingest_user_data: {e.message}")
        return
