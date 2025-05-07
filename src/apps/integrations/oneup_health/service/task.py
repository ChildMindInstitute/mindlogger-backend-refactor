import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import httpx

from apps.answers.crud.answers import AnswersEHRCRUD
from apps.answers.deps.preprocess_arbitrary import get_answer_session, preprocess_arbitrary_url
from apps.answers.domain import AnswerEHR, EHRIngestionStatus
from apps.integrations.oneup_health.service.oneup_health import OneupHealthService
from apps.shared.exception import BaseError
from broker import broker
from config import settings
from infrastructure.database import atomic, session_manager
from infrastructure.logger import logger

__all__ = ["task_ingest_user_data"]


def _exponential_backoff(retry_count) -> int:
    """
    Calculate exponential backoff time for retries with jitter.

    Implements exponential backoff algorithm: base_delay * 2^retry_count
    with jitter between 0.75x-1.25x of calculated delay

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
    return round(delay)


async def _process_data_transfer(
    session,
    applet_id: uuid.UUID,
    unique_id: uuid.UUID,
    activity_id: uuid.UUID,
    oneup_user_id: int,
    start_date: datetime | None,
) -> str | None:
    """
    Process the OneUp Health data transfer for a subject.

    Args:
        session: Database session
        applet_id (uuid.UUID): The unique identifier for the applet
        unique_id (uuid.UUID): The unique identifier for the user
        activity_id (uuid.UUID): The unique identifier for the activity
        oneup_user_id (int): The OneUp Health user ID
        start_date (datetime): The start date of the transfer process

    Returns:
        bool: True if the data transfer is complete, False otherwise
    """

    try:
        oneup_health_service = OneupHealthService()
        # Check if transfer is completed or timed out
        # The `oneup_user_id` is mapped to a MindLogger activity submission
        # We can determine if the data ingestions triggered by this activity submission
        # by comparing the number of ingestion starts (`data-transfer-initiated`) to the number
        # of ingestion end events (`member-data-ingestion-completed` and `member-data-ingestion-timeout`
        # https://docs.1up.health/help-center/Content/en-US/connect-patient/patient-connect-audit-events.html#audit-event-types-and-subtypes
        counters = await oneup_health_service.check_audit_events(oneup_user_id, start_date)

        initiated_count = counters["initiated"]
        if initiated_count > 0:
            logger.info(f"Transfer initiated for OneUp Health user ID {oneup_user_id} ({initiated_count} transfers)")
            completed_count = counters["completed"]
            timeout_count = counters["timeout"]

            if completed_count + timeout_count == initiated_count:
                logger.info(f"{completed_count} Transfers completed for OneUp Health user ID {oneup_user_id}")
                if timeout_count > 0:
                    logger.warn(f"{timeout_count} Transfers timed out for OneUp Health user ID {oneup_user_id}")
                return await oneup_health_service.retrieve_patient_data(
                    session=session,
                    applet_id=applet_id,
                    unique_id=unique_id,
                    activity_id=activity_id,
                    oneup_user_id=oneup_user_id,
                )
    except httpx.RequestError as e:
        logger.error(f"Failed to process data transfer for OneUp Health user ID {oneup_user_id}")
        logger.exception(f"Error: {e}")

    return None


async def _schedule_retry(
    applet_id: uuid.UUID, unique_id: uuid.UUID, activity_id: uuid.UUID, start_date: datetime | None, retry_count: int
) -> bool:
    """
    Schedule a retry of the data ingestion task with exponential backoff.

    Args:
        applet_id (uuid.UUID): The unique identifier for the applet
        unique_id (uuid.UUID): The unique identifier for the user
        activity_history_id (str): The activity history ID
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
            .kiq(
                applet_id=applet_id,
                unique_id=unique_id,
                activity_id=activity_id,
                start_date=start_date,
                retry_count=retry_count,
            )
        )

    return delay > 0


@broker.task
async def task_ingest_user_data(
    applet_id: uuid.UUID,
    unique_id: uuid.UUID,
    activity_id: uuid.UUID,
    start_date: datetime | None = None,
    retry_count: int = 0,
) -> str | None:
    """
    Asynchronous task to ingest user health data from OneUp Health.

    This task polls for data transfer status and retrieves patient data when ready.
    If the transfer is not complete, it reschedules itself with exponential backoff.

    Args:
        applet_id (uuid.UUID): The unique identifier for the applet
        unique_id (uuid.UUID): The unique identifier for the user
        activity_id (uuid.UUID): The unique identifier for the activity
        start_date (datetime, optional): The start date of the transfer process
        retry_count (int): The current retry attempt count

    Returns:
        list | None: List of retrieved resources if successful, None otherwise
    """
    storage_path = None
    async with session_manager.get_session()() as session:
        info = await preprocess_arbitrary_url(applet_id=applet_id, session=session)

        async with asynccontextmanager(get_answer_session)(info) as answer_session:
            answer_session = answer_session if answer_session is not None else session
            try:
                async with atomic(answer_session):
                    answer_ehr = AnswerEHR(
                        submit_id=unique_id,
                        ehr_ingestion_status=EHRIngestionStatus.IN_PROGRESS,
                        activity_id=activity_id,
                    )
                    await AnswersEHRCRUD(session=session).upsert(answer_ehr)

                async with atomic(answer_session):
                    result = await OneupHealthService().get_oneup_user_id(unique_id=unique_id, activity_id=activity_id)
                    if result is None:
                        logger.info(f"ID {unique_id} has no OneUp Health user ID")
                        await AnswersEHRCRUD(session=answer_session).update_status(
                            submit_id=unique_id,
                            activity_id=activity_id,
                            status=EHRIngestionStatus.FAILED,
                        )
                        return None

                    oneup_user_id = result["oneup_user_id"]

                    # Process data transfer
                    storage_path = await _process_data_transfer(
                        session=session,
                        applet_id=applet_id,
                        unique_id=unique_id,
                        activity_id=activity_id,
                        oneup_user_id=oneup_user_id,
                        start_date=start_date,
                    )
                    if storage_path is None:
                        logger.info(f"Data transfer not complete for OneUp Health user ID {oneup_user_id}")
                        to_reschedule = await _schedule_retry(
                            applet_id=applet_id,
                            unique_id=unique_id,
                            activity_id=activity_id,
                            start_date=start_date,
                            retry_count=retry_count,
                        )
                        if not to_reschedule:
                            await AnswersEHRCRUD(session=answer_session).update_status(
                                submit_id=unique_id,
                                activity_id=activity_id,
                                status=EHRIngestionStatus.FAILED,
                            )
                        return None

                    logger.info(
                        f"Data transfer complete for OneUp Health user ID {oneup_user_id} and submit ID {unique_id}"
                    )
                    await AnswersEHRCRUD(session=answer_session).upsert(
                        AnswerEHR(
                            submit_id=unique_id,
                            ehr_ingestion_status=EHRIngestionStatus.COMPLETED,
                            activity_id=activity_id,
                            ehr_storage_uri=storage_path,
                        )
                    )
            except BaseError as e:
                logger.error(f"Error in task_ingest_user_data: {e.message}")
                async with atomic(answer_session):
                    await AnswersEHRCRUD(session=answer_session).update_status(
                        submit_id=unique_id, activity_id=activity_id, status=EHRIngestionStatus.FAILED
                    )
            return storage_path


async def trigger_erh_ingestion(applet_id: uuid.UUID, submit_id: uuid.UUID, activity_id: uuid.UUID) -> None:
    await task_ingest_user_data.kicker().kiq(applet_id=applet_id, unique_id=submit_id, activity_id=activity_id)
