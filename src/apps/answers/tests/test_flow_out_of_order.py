import datetime
import http
import uuid
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.crud.answers import AnswersCRUD
from apps.answers.domain import AppletAnswerCreate, ClientMeta, ItemAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain.applet_full import AppletFull
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users import User


class TestFlowOutOfOrderSubmission(BaseTest):
    answer_url = "/answers"

    async def test_out_of_order_submission_accepts_all_activities(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """Out-of-order uploads still finish the flow when last activity arrives first."""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # Flow with 3 activities
        submit_id = uuid.uuid4()

        # Simulate network issue: Activity C (last) arrives first with is_flow_completed=True
        data_c = answer_create.copy(deep=True)
        data_c.submit_id = submit_id
        data_c.applet_id = applet_with_flow.id
        data_c.flow_id = flow.id
        data_c.activity_id = flow.items[2].activity_id
        data_c.is_flow_completed = True

        response = await client.post(self.answer_url, data=data_c)
        assert response.status_code == http.HTTPStatus.CREATED, f"Failed to create activity C: {response.json()}"

        # Activity A arrives late (should be accepted)
        data_a = answer_create.copy(deep=True)
        data_a.submit_id = submit_id
        data_a.applet_id = applet_with_flow.id
        data_a.flow_id = flow.id
        data_a.activity_id = flow.items[0].activity_id
        data_a.is_flow_completed = False

        response = await client.post(self.answer_url, data=data_a)
        assert response.status_code == http.HTTPStatus.CREATED, f"Failed to create activity A: {response.json()}"

        # Activity B arrives last (should be accepted)
        data_b = answer_create.copy(deep=True)
        data_b.submit_id = submit_id
        data_b.applet_id = applet_with_flow.id
        data_b.flow_id = flow.id
        data_b.activity_id = flow.items[1].activity_id
        data_b.is_flow_completed = False

        response = await client.post(self.answer_url, data=data_b)
        assert response.status_code == http.HTTPStatus.CREATED, f"Failed to create activity B: {response.json()}"

    async def test_backend_marks_only_last_activity_complete_for_legacy_clients(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
        session: AsyncSession,
    ):
        """Legacy clients set completion on every activity; backend should mark only the last one."""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]
        submit_id = uuid.uuid4()

        for item in flow.items:
            data = answer_create.copy(deep=True)
            data.submit_id = submit_id
            data.applet_id = applet_with_flow.id
            data.flow_id = flow.id
            data.activity_id = item.activity_id
            data.is_flow_completed = True  # Legacy behaviour

            response = await client.post(self.answer_url, data=data)
            assert response.status_code == http.HTTPStatus.CREATED, response.json()

        stored_answers = await AnswersCRUD(session).get_by_submit_id(submit_id)
        assert stored_answers is not None
        assert len(stored_answers) == len(flow.items)
        backend_flags = [answer.is_flow_completed for answer in stored_answers]
        assert all(flag is False for flag in backend_flags[:-1])
        assert backend_flags[-1] is True

    async def test_duplicate_activity_rejected_after_flow_complete(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """Test that duplicate submissions are rejected after all activities are submitted"""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # Flow with 3 activities
        submit_id = uuid.uuid4()

        # Submit all activities in order
        for i, item in enumerate(flow.items):
            data = answer_create.copy(deep=True)
            data.submit_id = submit_id
            data.applet_id = applet_with_flow.id
            data.flow_id = flow.id
            data.activity_id = item.activity_id
            data.is_flow_completed = i == len(flow.items) - 1  # Last activity completes flow

            response = await client.post(self.answer_url, data=data)
            assert response.status_code == http.HTTPStatus.CREATED

        # Try to submit a duplicate of activity A (should be rejected)
        duplicate_data = answer_create.copy(deep=True)
        duplicate_data.submit_id = submit_id
        duplicate_data.applet_id = applet_with_flow.id
        duplicate_data.flow_id = flow.id
        duplicate_data.activity_id = flow.items[0].activity_id
        duplicate_data.is_flow_completed = False

        response = await client.post(self.answer_url, data=duplicate_data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Flow is already completed" in response.json()["result"][0]["message"]

    async def test_flow_with_duplicate_activities_handles_counts_correctly(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow_duplicated_activities: AppletFull,
    ):
        """Test flow where the same activity appears multiple times"""
        client.login(tom)
        flow = applet_with_flow_duplicated_activities.activity_flows[0]  # Flow with duplicate activities
        submit_id = uuid.uuid4()

        # Assume flow has activity A twice (at positions 0 and 2)
        # Submit first occurrence
        data1 = answer_create.copy(deep=True)
        data1.submit_id = submit_id
        data1.applet_id = applet_with_flow_duplicated_activities.id
        data1.flow_id = flow.id
        data1.activity_id = flow.items[0].activity_id
        data1.is_flow_completed = False

        response = await client.post(self.answer_url, data=data1)
        assert response.status_code == http.HTTPStatus.CREATED

        # Submit second occurrence should still be accepted
        data2 = answer_create.copy(deep=True)
        data2.submit_id = submit_id
        data2.applet_id = applet_with_flow_duplicated_activities.id
        data2.flow_id = flow.id
        data2.activity_id = flow.items[0].activity_id  # Same activity ID
        data2.is_flow_completed = True

        response = await client.post(self.answer_url, data=data2)
        assert response.status_code == http.HTTPStatus.CREATED

        # Third occurrence should be rejected as it exceeds expected count
        data3 = answer_create.copy(deep=True)
        data3.submit_id = submit_id
        data3.applet_id = applet_with_flow_duplicated_activities.id
        data3.flow_id = flow.id
        data3.activity_id = flow.items[0].activity_id
        data3.is_flow_completed = False

        response = await client.post(self.answer_url, data=data3)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Flow is already completed" in response.json()["result"][0]["message"]

    @patch("apps.answers.service.logger")
    async def test_late_submission_logs_correctly(
        self,
        mock_logger,
        session: AsyncSession,
        tom: User,
        applet_with_flow: AppletFull,
    ):
        """Test that late submissions are logged for monitoring (occurrence-based validation)"""
        service = AnswerService(session, tom.id)
        flow = applet_with_flow.activity_flows[1]
        submit_id = uuid.uuid4()

        # Create last activity with is_flow_completed=True (without created_at for occurrence-based validation)
        answer_c = AppletAnswerCreate(
            applet_id=applet_with_flow.id,
            version=applet_with_flow.version,
            submit_id=submit_id,
            flow_id=flow.id,
            activity_id=flow.items[2].activity_id,
            is_flow_completed=True,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[2].items[0].id],
                start_time=datetime.datetime.now(datetime.UTC),
                end_time=datetime.datetime.now(datetime.UTC),
                user_public_key="test_key",
            ),
            created_at=None,  # Use occurrence-based validation
            client=ClientMeta(app_id="test", app_version="1.0.0"),
        )

        await service.create_answer(answer_c)

        # Create late submission for first activity
        answer_a = AppletAnswerCreate(
            applet_id=applet_with_flow.id,
            version=applet_with_flow.version,
            submit_id=submit_id,
            flow_id=flow.id,
            activity_id=flow.items[0].activity_id,
            is_flow_completed=False,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                start_time=datetime.datetime.now(datetime.UTC),
                end_time=datetime.datetime.now(datetime.UTC),
                user_public_key="test_key",
            ),
            created_at=None,  # Use occurrence-based validation
            client=ClientMeta(app_id="test", app_version="1.0.0"),
        )

        await service.create_answer(answer_a)

        # Verify logging was called
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args[0][0]
        assert "Allowing flow submission" in log_call

    async def test_normal_flow_behavior_unchanged(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """Test that normal in-order submissions continue to work as before"""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]
        submit_id = uuid.uuid4()

        # Submit activities in correct order
        for i, item in enumerate(flow.items):
            data = answer_create.copy(deep=True)
            data.submit_id = submit_id
            data.applet_id = applet_with_flow.id
            data.flow_id = flow.id
            data.activity_id = item.activity_id
            data.is_flow_completed = i == len(flow.items) - 1

            response = await client.post(self.answer_url, data=data)
            assert response.status_code == http.HTTPStatus.CREATED

        # Verify flow is complete - try to submit first activity again
        duplicate_data = answer_create.copy(deep=True)
        duplicate_data.submit_id = submit_id
        duplicate_data.applet_id = applet_with_flow.id
        duplicate_data.flow_id = flow.id
        duplicate_data.activity_id = flow.items[0].activity_id

        response = await client.post(self.answer_url, data=duplicate_data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Flow is already completed" in response.json()["result"][0]["message"]

    async def test_partial_out_of_order_with_missing_activities(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """Test that flow remains open when some activities are still missing"""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # Flow with 3 activities
        submit_id = uuid.uuid4()

        # First, submit activity A (first activity) to establish the flow
        data_a = answer_create.copy(deep=True)
        data_a.submit_id = submit_id
        data_a.applet_id = applet_with_flow.id
        data_a.flow_id = flow.id
        data_a.activity_id = flow.items[0].activity_id
        data_a.is_flow_completed = False

        response = await client.post(self.answer_url, data=data_a)
        assert response.status_code == http.HTTPStatus.CREATED

        # Submit activity C with is_flow_completed=True (skipping B)
        data_c = answer_create.copy(deep=True)
        data_c.submit_id = submit_id
        data_c.applet_id = applet_with_flow.id
        data_c.flow_id = flow.id
        data_c.activity_id = flow.items[2].activity_id
        data_c.is_flow_completed = True

        response = await client.post(self.answer_url, data=data_c)
        assert response.status_code == http.HTTPStatus.CREATED

        # Activity B should still be accepted (flow not truly complete yet)
        data_b = answer_create.copy(deep=True)
        data_b.submit_id = submit_id
        data_b.applet_id = applet_with_flow.id
        data_b.flow_id = flow.id
        data_b.activity_id = flow.items[1].activity_id
        data_b.is_flow_completed = False

        response = await client.post(self.answer_url, data=data_b)
        assert response.status_code == http.HTTPStatus.CREATED

        # Now all activities are submitted, flow should be closed
        duplicate_data = answer_create.copy(deep=True)
        duplicate_data.submit_id = submit_id
        duplicate_data.applet_id = applet_with_flow.id
        duplicate_data.flow_id = flow.id
        duplicate_data.activity_id = flow.items[0].activity_id

        response = await client.post(self.answer_url, data=duplicate_data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Flow is already completed" in response.json()["result"][0]["message"]

    async def test_timestamp_allows_duplicate_activities_with_different_timestamps(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """When created_at is provided, different timestamps allow duplicate activities"""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]
        submit_id = uuid.uuid4()

        # Submit same activity with first timestamp
        data1 = answer_create.copy(deep=True)
        data1.submit_id = submit_id
        data1.applet_id = applet_with_flow.id
        data1.flow_id = flow.id
        data1.activity_id = flow.items[0].activity_id
        data1.created_at = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
        data1.is_flow_completed = False

        response = await client.post(self.answer_url, data=data1)
        assert response.status_code == http.HTTPStatus.CREATED, f"First submission failed: {response.json()}"

        # Submit same activity with different timestamp (should be accepted)
        data2 = answer_create.copy(deep=True)
        data2.submit_id = submit_id
        data2.applet_id = applet_with_flow.id
        data2.flow_id = flow.id
        data2.activity_id = flow.items[0].activity_id
        data2.created_at = datetime.datetime(2024, 1, 1, 12, 30, 0, tzinfo=datetime.UTC)
        data2.is_flow_completed = False

        response = await client.post(self.answer_url, data=data2)
        assert response.status_code == http.HTTPStatus.CREATED, f"Second submission with different timestamp failed: {response.json()}"

    async def test_timestamp_rejects_duplicate_with_same_timestamp(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """When created_at is provided, same timestamp rejects duplicate"""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]
        submit_id = uuid.uuid4()
        timestamp = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

        # Submit activity with timestamp
        data1 = answer_create.copy(deep=True)
        data1.submit_id = submit_id
        data1.applet_id = applet_with_flow.id
        data1.flow_id = flow.id
        data1.activity_id = flow.items[0].activity_id
        data1.created_at = timestamp
        data1.is_flow_completed = False

        response = await client.post(self.answer_url, data=data1)
        assert response.status_code == http.HTTPStatus.CREATED

        # Try to submit same activity with same timestamp (should be rejected)
        data2 = answer_create.copy(deep=True)
        data2.submit_id = submit_id
        data2.applet_id = applet_with_flow.id
        data2.flow_id = flow.id
        data2.activity_id = flow.items[0].activity_id
        data2.created_at = timestamp
        data2.is_flow_completed = False

        response = await client.post(self.answer_url, data=data2)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Duplicate answer with same timestamp" in response.json()["result"][0]["message"]

    async def test_timestamp_bypasses_occurrence_limits(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """When created_at is provided, occurrence counting is bypassed"""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]
        submit_id = uuid.uuid4()

        # Submit same activity multiple times with different timestamps
        # This would normally be rejected by occurrence counting
        for i in range(5):
            data = answer_create.copy(deep=True)
            data.submit_id = submit_id
            data.applet_id = applet_with_flow.id
            data.flow_id = flow.id
            data.activity_id = flow.items[0].activity_id
            data.created_at = datetime.datetime(2024, 1, 1, 12, i, 0, tzinfo=datetime.UTC)
            data.is_flow_completed = False

            response = await client.post(self.answer_url, data=data)
            assert response.status_code == http.HTTPStatus.CREATED, f"Submission {i} failed: {response.json()}"

    async def test_check_existence_consistent_with_upload_validation(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """Check-existence endpoint should match upload validation behavior"""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]
        submit_id = uuid.uuid4()
        timestamp = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

        # Submit activity with timestamp
        data = answer_create.copy(deep=True)
        data.submit_id = submit_id
        data.applet_id = applet_with_flow.id
        data.flow_id = flow.id
        data.activity_id = flow.items[0].activity_id
        data.created_at = timestamp
        data.is_flow_completed = False

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        # Check existence with same timestamp (should return true)
        check_data = {
            "applet_id": str(applet_with_flow.id),
            "activity_id": str(flow.items[0].activity_id),
            "submit_id": str(submit_id),
            "created_at": int(timestamp.timestamp() * 1000),
        }
        response = await client.post("/answers/check-existence", data=check_data)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["exists"] is True

        # Check existence with different timestamp (should return false)
        check_data["created_at"] = int(datetime.datetime(2024, 1, 1, 13, 0, 0, tzinfo=datetime.UTC).timestamp() * 1000)
        response = await client.post("/answers/check-existence", data=check_data)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["exists"] is False
