import re
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_httpx import HTTPXMock

from apps.answers.crud.answers import AnswersEHRCRUD
from apps.answers.domain import EHRIngestionStatus
from apps.applets.domain.applet_full import AppletFull
from apps.integrations.oneup_health.service.task import task_ingest_user_data


class TestTaskIngestUserData:
    @pytest.mark.asyncio
    async def test_success(self, session, applet_one: AppletFull, httpx_mock: HTTPXMock):
        # mock get user
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="GET",
            json={
                "entry": [{"oneup_user_id": 1}],
                "success": True,
            },
        )

        # mock audit event
        httpx_mock.add_response(
            url=re.compile(
                ".*/r4/AuditEvent\\?subtype=data-transfer-initiated%2Cmember-data-ingestion-completed%2Cmember-data-ingestion-timeout.*"
            ),
            method="GET",
            json={
                "entry": [
                    {
                        "resource": {"id": "fakeid", "subtype": [{"code": "data-transfer-initiated"}]},
                    },
                    {
                        "resource": {"id": "fakeid", "subtype": [{"code": "member-data-ingestion-completed"}]},
                    },
                ],
                "total": 4,
            },
        )

        # mock patient resources
        httpx_mock.add_response(
            url=re.compile(".*/r4/Patient"),
            method="GET",
            json={
                "total": 1,
                "entry": [
                    {
                        "fullUrl": "https://fake.url/r4/Patient/fakeid",
                        "resource": {"id": "health_provider_id_1"},
                    }
                ],
            },
        )
        # mock patient resources data
        httpx_mock.add_response(
            url=re.compile(".*/r4/Patient/fakeid/\\$everything"),
            method="GET",
            json={
                "total": 2,
                "entry": [
                    {
                        "fullUrl": "https://fake.url/r4/AllergyIntolerance/fakeid",
                        "resource": {"id": "resource_id_1"},
                    },
                    {
                        "fullUrl": "https://fake.url/r4/AllergyIntolerance/fakeid2",
                        "resource": {"id": "resource_id_2"},
                    },
                ],
            },
        )

        with patch(
            "apps.integrations.oneup_health.service.ehr_storage._EHRStorage.upload_resources"
        ) as upload_resources:
            # Mock the storage to return a path
            upload_resources.return_value = "fake/storage/path"

            submit_id = uuid.uuid4()
            task = await task_ingest_user_data.kicker().kiq(
                applet_id=applet_one.id, unique_id=submit_id, activity_history_id=f"{uuid.uuid4()}_1.0.0"
            )
            result = await task.wait_result()

            assert result.return_value == "fake/storage/path"
            assert upload_resources.called

            answers_ehr = await AnswersEHRCRUD(session).get_by_submit_id(submit_id)
            assert answers_ehr is not None
            assert answers_ehr.ehr_storage_uri == "fake/storage/path"
            assert answers_ehr.ehr_ingestion_status == EHRIngestionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_no_oneup_user_id(self, session, httpx_mock: HTTPXMock):
        # mock ge user
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="GET",
            json={
                "entry": [],
                "success": True,
            },
        )

        applet_id = uuid.uuid4()
        unique_id = uuid.uuid4()
        result = await task_ingest_user_data(applet_id, unique_id, activity_history_id=f"{uuid.uuid4()}_1.0.0")
        assert result is None

        answers_ehr = await AnswersEHRCRUD(session).get_by_submit_id(submit_id=unique_id)
        assert answers_ehr is not None
        assert answers_ehr.ehr_storage_uri is None
        assert answers_ehr.ehr_ingestion_status == EHRIngestionStatus.FAILED

    @pytest.mark.asyncio
    async def test_transfer_not_complete(self, session, httpx_mock: HTTPXMock):
        # mock ge user
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="GET",
            json={
                "entry": [{"oneup_user_id": 1}],
                "success": True,
            },
        )
        with patch(
            "apps.integrations.oneup_health.service.task._process_data_transfer", new=AsyncMock(return_value=None)
        ) as mock_process:
            with patch("apps.integrations.oneup_health.service.task._schedule_retry", new=AsyncMock()) as mock_retry:
                applet_id = uuid.uuid4()
                unique_id = uuid.uuid4()
                result = await task_ingest_user_data(applet_id, unique_id, activity_history_id=f"{uuid.uuid4()}_1.0.0")
                assert result is None
                assert mock_process.called
                assert mock_retry.called

                answers_ehr = await AnswersEHRCRUD(session).get_by_submit_id(submit_id=unique_id)
                assert answers_ehr is not None
                assert answers_ehr.ehr_storage_uri is None
                assert answers_ehr.ehr_ingestion_status == EHRIngestionStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test the exponential backoff calculation with different retry counts."""
        from apps.integrations.oneup_health.service.task import _exponential_backoff
        from config import settings

        # Save original values to restore after test
        original_base_delay = settings.oneup_health.base_backoff_delay
        original_max_delay = settings.oneup_health.max_backoff_delay

        # Set test values
        settings.oneup_health.base_backoff_delay = 2
        settings.oneup_health.max_backoff_delay = 30

        try:
            # Test retry count 0
            delay_0 = _exponential_backoff(0)
            assert 1 <= delay_0 <= 3  # With jitter between 0.75-1.25, should be between 1-3

            # Test retry count 1
            delay_1 = _exponential_backoff(1)
            assert 3 <= delay_1 <= 5  # Base * 2^1 * jitter

            # Test retry count 3
            delay_3 = _exponential_backoff(3)
            assert 12 <= delay_3 <= 20  # Base * 2^3 * jitter

            # Test max delay (should return 0 when max delay is reached)
            settings.oneup_health.max_backoff_delay = 10
            delay_max = _exponential_backoff(3)
            assert delay_max == 0
        finally:
            # Restore original values
            settings.oneup_health.base_backoff_delay = original_base_delay
            settings.oneup_health.max_backoff_delay = original_max_delay

    @pytest.mark.asyncio
    async def test_process_data_transfer_partial_completion(
        self, session, applet_one: AppletFull, httpx_mock: HTTPXMock
    ):
        """Test the _process_data_transfer function with partial completion."""
        from apps.integrations.oneup_health.service.task import _process_data_transfer

        # Mock audit events
        httpx_mock.add_response(
            url=re.compile(
                ".*/r4/AuditEvent\\?subtype=data-transfer-initiated%2Cmember-data-ingestion-completed%2Cmember-data-ingestion-timeout.*"
            ),
            method="GET",
            json={
                "entry": [
                    {
                        "resource": {"id": "fakeid", "subtype": [{"code": "data-transfer-initiated"}]},
                    },
                    {
                        "resource": {"id": "fakeid2", "subtype": [{"code": "data-transfer-initiated"}]},
                    },
                    {
                        "resource": {"id": "fakeid3", "subtype": [{"code": "data-transfer-initiated"}]},
                    },
                    {
                        "resource": {"id": "fakeid", "subtype": [{"code": "member-data-ingestion-completed"}]},
                    },
                ],
                "total": 4,
            },
        )

        unique_id = uuid.uuid4()
        oneup_user_id = 1
        start_date = None

        result = await _process_data_transfer(session, applet_one.id, unique_id, oneup_user_id, start_date)

        # Should return None since not all transfers are complete
        assert result is None

    @pytest.mark.asyncio
    async def test_process_data_transfer_with_timeouts(self, session, applet_one: AppletFull, httpx_mock: HTTPXMock):
        """Test the _process_data_transfer function with some timeouts."""
        from apps.integrations.oneup_health.service.task import _process_data_transfer

        # Mock audit events
        httpx_mock.add_response(
            url=re.compile(
                ".*/r4/AuditEvent\\?subtype=data-transfer-initiated%2Cmember-data-ingestion-completed%2Cmember-data-ingestion-timeout.*"
            ),
            method="GET",
            json={
                "entry": [
                    {
                        "resource": {"id": "fakeid", "subtype": [{"code": "data-transfer-initiated"}]},
                    },
                    {
                        "resource": {"id": "fakeid2", "subtype": [{"code": "data-transfer-initiated"}]},
                    },
                    {
                        "resource": {"id": "fakeid3", "subtype": [{"code": "data-transfer-initiated"}]},
                    },
                    {
                        "resource": {"id": "fakeid", "subtype": [{"code": "member-data-ingestion-completed"}]},
                    },
                    {
                        "resource": {"id": "fakeid2", "subtype": [{"code": "member-data-ingestion-timeout"}]},
                    },
                    {
                        "resource": {"id": "fakeid3", "subtype": [{"code": "member-data-ingestion-timeout"}]},
                    },
                ],
                "total": 6,
            },
        )

        # Mock patient resources
        httpx_mock.add_response(
            url=re.compile(".*/r4/Patient"),
            method="GET",
            json={
                "total": 1,
                "entry": [
                    {
                        "fullUrl": "https://fake.url/r4/Patient/fakeid",
                        "resource": {"id": "health_provider_id_1"},
                    }
                ],
            },
        )

        # Mock patient resources data
        httpx_mock.add_response(
            url=re.compile(".*/r4/Patient/fakeid/\\$everything"),
            method="GET",
            json={
                "total": 1,
                "entry": [
                    {
                        "fullUrl": "https://fake.url/r4/Observation/fakeid",
                        "resource": {"id": "resource_id_1"},
                    }
                ],
            },
        )

        unique_id = uuid.uuid4()
        oneup_user_id = 1
        start_date = None

        with patch(
            "apps.integrations.oneup_health.service.ehr_storage._EHRStorage.upload_resources"
        ) as upload_resources:
            upload_resources.return_value = "fake/storage/path"

            result = await _process_data_transfer(session, applet_one.id, unique_id, oneup_user_id, start_date)

            assert result == "fake/storage/path"
            assert upload_resources.called

    @pytest.mark.asyncio
    async def test_process_data_transfer_http_error(self, session, applet_one: AppletFull, httpx_mock: HTTPXMock):
        """Test the _process_data_transfer function with HTTP error."""
        import httpx

        from apps.integrations.oneup_health.service.task import _process_data_transfer

        # Mock HTTP error for audit events
        httpx_mock.add_exception(
            url=re.compile(
                ".*/r4/AuditEvent\\?subtype=data-transfer-initiated%2Cmember-data-ingestion-completed%2Cmember-data-ingestion-timeout.*"
            ),
            exception=httpx.RequestError("Connection error"),
        )

        # Test with session mock
        unique_id = uuid.uuid4()
        oneup_user_id = 1
        start_date = None

        result = await _process_data_transfer(session, applet_one.id, unique_id, oneup_user_id, start_date)

        # Should return None due to the HTTP error
        assert result is None

    @pytest.mark.asyncio
    async def test_schedule_retry(self, applet_one: AppletFull):
        from apps.integrations.oneup_health.service.task import _schedule_retry

        unique_id = uuid.uuid4()
        start_date = None
        retry_count = 2

        with patch("apps.integrations.oneup_health.service.task.task_ingest_user_data") as mock_task:
            kicker = MagicMock()
            with_labels = MagicMock()
            kiq = AsyncMock()

            mock_task.kicker.return_value = kicker
            kicker.with_labels.return_value = with_labels
            with_labels.kiq = kiq

            with patch(
                "apps.integrations.oneup_health.service.task._exponential_backoff",
                return_value=10,
            ) as mock_backoff:
                await _schedule_retry(applet_one.id, unique_id, start_date, retry_count)

                mock_backoff.assert_called_once_with(retry_count)
                mock_task.kicker.assert_called_once()
                kicker.with_labels.assert_called_once_with(delay=10)
                kiq.assert_awaited_once_with(
                    applet_id=applet_one.id,
                    unique_id=unique_id,
                    start_date=start_date,
                    retry_count=retry_count + 1,
                )
