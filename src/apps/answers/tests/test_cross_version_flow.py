import datetime
import http
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.domain import AppletAnswerCreate
from apps.answers.domain.answers import CompletedEntity
from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service.applet import AppletService
from apps.shared.enums import Language
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User


def _applet_update_from_full(applet: AppletFull) -> AppletUpdate:
    """Build an AppletUpdate from an AppletFull, fixing flow items activity_key mapping.

    AppletFull flow items have activity_id+order, but AppletUpdate/FlowItemCreate
    requires activity_key. This helper maps activity_id → key from the activities list.
    """
    data = applet.model_dump()
    activity_id_to_key = {str(a["id"]): a["key"] for a in data["activities"]}
    for flow in data["activity_flows"]:
        for item in flow["items"]:
            item["activity_key"] = activity_id_to_key[str(item["activity_id"])]
    return AppletUpdate(**data)


class TestCrossVersionFlowSubmission(BaseTest):
    """Test that flow submissions work across applet version changes."""

    answer_url = "/answers"

    async def test_flow_submission_adopts_existing_version(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """When an applet version changes mid-flow, the submission should adopt
        the version of the existing answer group instead of raising WrongAnswerGroupVersion."""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # Flow with 3 activities
        submit_id = uuid.uuid4()
        original_version = applet_with_flow.version

        # Submit first activity at version 1
        data_a = answer_create.model_copy(deep=True)
        data_a.submit_id = submit_id
        data_a.applet_id = applet_with_flow.id
        data_a.flow_id = flow.id
        data_a.activity_id = flow.items[0].activity_id
        data_a.is_flow_completed = False
        data_a.version = original_version

        response = await client.post(self.answer_url, data=data_a)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Update the applet to bump the version
        srv = AppletService(session, tom.id)
        update_data = _applet_update_from_full(applet_with_flow)
        update_data.display_name = "Updated applet"
        updated_applet = await srv.update(applet_with_flow.id, update_data)
        new_version = updated_applet.version
        assert new_version != original_version, "Version should have changed after update"

        # Submit second activity with NEW version — should succeed by adopting original version
        data_b = answer_create.model_copy(deep=True)
        data_b.submit_id = submit_id
        data_b.applet_id = applet_with_flow.id
        data_b.flow_id = flow.id
        data_b.activity_id = flow.items[1].activity_id
        data_b.is_flow_completed = False
        data_b.version = new_version

        response = await client.post(self.answer_url, data=data_b)
        assert response.status_code == http.HTTPStatus.CREATED, (
            f"Cross-version flow submission should succeed: {response.json()}"
        )

    async def test_cross_version_flow_completion(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """A flow started at v1 can be completed at v2 with is_flow_completed=True."""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # 3 activities
        submit_id = uuid.uuid4()
        original_version = applet_with_flow.version

        # Submit activities A and B at original version
        for i in range(2):
            data = answer_create.model_copy(deep=True)
            data.submit_id = submit_id
            data.applet_id = applet_with_flow.id
            data.flow_id = flow.id
            data.activity_id = flow.items[i].activity_id
            data.is_flow_completed = False
            data.version = original_version
            response = await client.post(self.answer_url, data=data)
            assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Update applet to bump version
        srv = AppletService(session, tom.id)
        update_data = _applet_update_from_full(applet_with_flow)
        update_data.display_name = "Updated applet v2"
        updated_applet = await srv.update(applet_with_flow.id, update_data)
        new_version = updated_applet.version

        # Submit last activity at new version with is_flow_completed=True
        data_c = answer_create.model_copy(deep=True)
        data_c.submit_id = submit_id
        data_c.applet_id = applet_with_flow.id
        data_c.flow_id = flow.id
        data_c.activity_id = flow.items[2].activity_id
        data_c.is_flow_completed = True
        data_c.version = new_version

        response = await client.post(self.answer_url, data=data_c)
        assert response.status_code == http.HTTPStatus.CREATED, (
            f"Cross-version flow completion should succeed: {response.json()}"
        )

        # Verify the flow is marked complete — subsequent submission should be rejected
        data_dup = answer_create.model_copy(deep=True)
        data_dup.submit_id = submit_id
        data_dup.applet_id = applet_with_flow.id
        data_dup.flow_id = flow.id
        data_dup.activity_id = flow.items[0].activity_id
        data_dup.version = new_version

        response = await client.post(self.answer_url, data=data_dup)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert "Flow is already completed" in response.json()["result"][0]["message"]

    async def test_non_flow_submission_still_rejects_version_mismatch(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        answer_create: AppletAnswerCreate,
        applet: AppletFull,
    ):
        """Non-flow (standalone activity) submissions still raise WrongAnswerGroupVersion."""
        client.login(tom)
        submit_id = uuid.uuid4()

        # Submit first answer at current version
        data1 = answer_create.model_copy(deep=True)
        data1.submit_id = submit_id
        data1.version = applet.version

        response = await client.post(self.answer_url, data=data1)
        assert response.status_code == http.HTTPStatus.CREATED

        # Update applet to bump version
        srv = AppletService(session, tom.id)
        update_data = _applet_update_from_full(applet)
        update_data.display_name = "Updated standalone"
        updated_applet = await srv.update(applet.id, update_data)

        # Submit same activity with new version — should fail (no flow_id)
        data2 = answer_create.model_copy(deep=True)
        data2.submit_id = submit_id
        data2.version = updated_applet.version

        response = await client.post(self.answer_url, data=data2)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST


class TestVersionAwareActivityEndpoint(BaseTest):
    """Test GET /activities/{id}?version=... for fetching from history."""

    activity_url = "/activities/{activity_id}"

    async def test_fetch_activity_by_version(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        applet_with_flow: AppletFull,
    ):
        """Fetch an activity at a specific historical version."""
        client.login(tom)
        activity = applet_with_flow.activities[0]
        version = applet_with_flow.version

        response = await client.get(
            self.activity_url.format(activity_id=activity.id),
            {"version": version},
        )
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["name"] == activity.name

    async def test_fetch_deleted_activity_from_history(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        applet_with_flow: AppletFull,
    ):
        """After deleting an activity, it can still be fetched from history using version."""
        client.login(tom)
        original_version = applet_with_flow.version
        original_activity = applet_with_flow.activities[0]
        original_activity_name = original_activity.name

        # Update applet, removing the first activity and rebuilding flows
        srv = AppletService(session, tom.id)
        data = applet_with_flow.model_dump()
        # Keep only activities[1] and activities[2] (remove activities[0])
        remaining_activities = data["activities"][1:]
        data["activities"] = remaining_activities
        # Update flows to only reference remaining activities
        data["activity_flows"] = [
            {
                "name": "flow",
                "description": {Language.ENGLISH: "description"},
                "items": [{"activity_key": remaining_activities[0]["key"]}],
            },
        ]
        update_data = AppletUpdate(**data)
        await srv.update(applet_with_flow.id, update_data)

        # Fetching the deleted activity without version should fail
        response = await client.get(
            self.activity_url.format(activity_id=original_activity.id),
        )
        assert response.status_code != http.HTTPStatus.OK

        # Fetching with the original version should succeed from history
        response = await client.get(
            self.activity_url.format(activity_id=original_activity.id),
            {"version": original_version},
        )
        assert response.status_code == http.HTTPStatus.OK, (
            f"Should be able to fetch deleted activity from history: {response.json()}"
        )
        result = response.json()["result"]
        assert result["name"] == original_activity_name

    async def test_fetch_activity_without_version_returns_current(
        self,
        client: TestClient,
        tom: User,
        applet_with_flow: AppletFull,
    ):
        """Without version param, normal behavior returns current activity."""
        client.login(tom)
        activity = applet_with_flow.activities[0]

        response = await client.get(
            self.activity_url.format(activity_id=activity.id),
        )
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["name"] == activity.name


class TestFilterActivityFlowsAcrossVersions(BaseTest):
    """Test _filter_activity_flows groups flows by unversioned ID across versions."""

    completions_url = "/answers/applet/{applet_id}/completions"
    answer_url = "/answers"

    async def test_in_progress_flow_survives_version_update(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """An in-progress flow at v1 should appear in completions after applet is updated to v2."""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # 3-activity flow
        submit_id = uuid.uuid4()
        original_version = applet_with_flow.version

        # Submit first activity (flow is now in-progress)
        data = answer_create.model_copy(deep=True)
        data.submit_id = submit_id
        data.applet_id = applet_with_flow.id
        data.flow_id = flow.id
        data.activity_id = flow.items[0].activity_id
        data.is_flow_completed = False
        data.version = original_version

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        # Update applet to create v2
        srv = AppletService(session, tom.id)
        update_data = _applet_update_from_full(applet_with_flow)
        update_data.display_name = "Updated"
        await srv.update(applet_with_flow.id, update_data)

        # Query completions with includeInProgress=true
        response = await client.get(
            self.completions_url.format(applet_id=applet_with_flow.id),
            query={
                "fromDate": (datetime.date.today() - datetime.timedelta(days=30)).isoformat(),
                "includeInProgress": "true",
            },
        )
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        activity_flows = result["activityFlows"]

        # The in-progress flow should still appear
        assert len(activity_flows) >= 1, "In-progress flow should survive version update"
        in_progress = [f for f in activity_flows if f["isFlowCompleted"] is False]
        assert len(in_progress) == 1, "Should have exactly one in-progress flow"
        assert in_progress[0]["id"] == str(flow.id)

    async def test_completions_includes_flow_activity_ids_for_in_progress(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """In-progress flows should include flowActivityIds and flowName in completions."""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # 3-activity flow
        submit_id = uuid.uuid4()

        # Submit first activity
        data = answer_create.model_copy(deep=True)
        data.submit_id = submit_id
        data.applet_id = applet_with_flow.id
        data.flow_id = flow.id
        data.activity_id = flow.items[0].activity_id
        data.is_flow_completed = False

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        # Query completions
        response = await client.get(
            self.completions_url.format(applet_id=applet_with_flow.id),
            query={
                "fromDate": (datetime.date.today() - datetime.timedelta(days=30)).isoformat(),
                "includeInProgress": "true",
            },
        )
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        in_progress = [f for f in result["activityFlows"] if f["isFlowCompleted"] is False]

        assert len(in_progress) == 1
        flow_data = in_progress[0]

        # Should include flowActivityIds (ordered activity UUIDs from flow_item_histories)
        assert "flowActivityIds" in flow_data, "In-progress flow should have flowActivityIds"
        flow_activity_ids = flow_data["flowActivityIds"]
        assert len(flow_activity_ids) == 3, "Flow has 3 activities"
        expected_ids = [str(item.activity_id) for item in flow.items]
        assert flow_activity_ids == expected_ids

        # Should include flowName
        assert "flowName" in flow_data, "In-progress flow should have flowName"
        assert flow_data["flowName"] == flow.name

    async def test_completed_flows_exclude_flow_activity_ids(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """Completed flows should NOT include flowActivityIds or flowName in serialization."""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # 3-activity flow
        submit_id = uuid.uuid4()

        # Submit all activities to complete the flow
        for i, item in enumerate(flow.items):
            data = answer_create.model_copy(deep=True)
            data.submit_id = submit_id
            data.applet_id = applet_with_flow.id
            data.flow_id = flow.id
            data.activity_id = item.activity_id
            data.is_flow_completed = i == len(flow.items) - 1

            response = await client.post(self.answer_url, data=data)
            assert response.status_code == http.HTTPStatus.CREATED

        # Query completions
        response = await client.get(
            self.completions_url.format(applet_id=applet_with_flow.id),
            query={
                "fromDate": (datetime.date.today() - datetime.timedelta(days=30)).isoformat(),
            },
        )
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        completed = [f for f in result["activityFlows"] if f.get("isFlowCompleted") is True]

        assert len(completed) >= 1
        flow_data = completed[0]

        # flowActivityIds and flowName should be excluded (None → omitted by model_serializer)
        assert "flowActivityIds" not in flow_data, "Completed flows should not include flowActivityIds"
        assert "flowName" not in flow_data, "Completed flows should not include flowName"

    async def test_cross_version_filter_picks_latest_in_progress(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """When flow has in-progress at v1 (1 activity) and v2 (2 activities),
        the filter should pick v2 as it's the latest version."""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # 3-activity flow
        original_version = applet_with_flow.version

        # Submit first activity at v1
        submit_id_v1 = uuid.uuid4()
        data_v1 = answer_create.model_copy(deep=True)
        data_v1.submit_id = submit_id_v1
        data_v1.applet_id = applet_with_flow.id
        data_v1.flow_id = flow.id
        data_v1.activity_id = flow.items[0].activity_id
        data_v1.is_flow_completed = False
        data_v1.version = original_version
        # Set end_time to an earlier time
        data_v1.answer.end_time = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
        data_v1.answer.start_time = datetime.datetime(2024, 1, 1, 11, 0, 0, tzinfo=datetime.UTC)

        response = await client.post(self.answer_url, data=data_v1)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Update applet to v2
        srv = AppletService(session, tom.id)
        update_data = _applet_update_from_full(applet_with_flow)
        update_data.display_name = "v2"
        updated_applet = await srv.update(applet_with_flow.id, update_data)
        v2 = updated_applet.version

        # Submit first two activities at v2 with a new submit_id
        submit_id_v2 = uuid.uuid4()
        for i in range(2):
            data_v2 = answer_create.model_copy(deep=True)
            data_v2.submit_id = submit_id_v2
            data_v2.applet_id = applet_with_flow.id
            data_v2.flow_id = flow.id
            data_v2.activity_id = flow.items[i].activity_id
            data_v2.is_flow_completed = False
            data_v2.version = v2
            data_v2.answer.start_time = datetime.datetime(2024, 1, 2, 11, 0, 0, tzinfo=datetime.UTC)
            data_v2.answer.end_time = datetime.datetime(2024, 1, 2, 12, 0, 0, tzinfo=datetime.UTC)

            response = await client.post(self.answer_url, data=data_v2)
            assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Query completions
        response = await client.get(
            self.completions_url.format(applet_id=applet_with_flow.id),
            query={
                "fromDate": "2024-01-01",
                "includeInProgress": "true",
            },
        )
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        in_progress = [f for f in result["activityFlows"] if f["isFlowCompleted"] is False]

        # _filter_activity_flows groups by unversioned flow ID, so both v1 and v2
        # submissions are compared. v2 should win (higher version, more activities done).
        assert len(in_progress) == 1, (
            f"Should have exactly 1 in-progress flow after cross-version filter, got {len(in_progress)}"
        )
        # The winner should be the v2 submission (activity_flow_order=2, version=v2)
        assert in_progress[0]["activityFlowOrder"] == 2


class TestPopulateActivityFlowOrders(BaseTest):
    """Test that activity_flow_order uses COUNT-based logic."""

    completions_url = "/answers/applet/{applet_id}/completions"
    answer_url = "/answers"

    async def test_activity_flow_order_is_count_based(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        """activity_flow_order should equal the count of answers for (flow_history_id, submit_id)."""
        client.login(tom)
        flow = applet_with_flow.activity_flows[1]  # 3-activity flow
        submit_id = uuid.uuid4()

        # Submit 2 of 3 activities
        for i in range(2):
            data = answer_create.model_copy(deep=True)
            data.submit_id = submit_id
            data.applet_id = applet_with_flow.id
            data.flow_id = flow.id
            data.activity_id = flow.items[i].activity_id
            data.is_flow_completed = False

            response = await client.post(self.answer_url, data=data)
            assert response.status_code == http.HTTPStatus.CREATED

        # Query completions
        response = await client.get(
            self.completions_url.format(applet_id=applet_with_flow.id),
            query={
                "fromDate": (datetime.date.today() - datetime.timedelta(days=30)).isoformat(),
                "includeInProgress": "true",
            },
        )
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        in_progress = [f for f in result["activityFlows"] if f["isFlowCompleted"] is False]

        assert len(in_progress) == 1
        # 2 activities submitted → activityFlowOrder = 2
        assert in_progress[0]["activityFlowOrder"] == 2, (
            f"Expected activityFlowOrder=2 (count of submitted activities), got {in_progress[0]['activityFlowOrder']}"
        )


class TestCompletedEntitySerialization(BaseTest):
    """Test CompletedEntity model serialization."""

    def test_completed_entity_excludes_none_flow_fields(self):
        """flowActivityIds and flowName should be excluded from JSON when None."""
        entity = CompletedEntity(
            id=f"{uuid.uuid4()}_1.0.0",
            answer_id=uuid.uuid4(),
            submit_id=uuid.uuid4(),
            version="1.0.0",
            local_end_date=datetime.date.today(),
            local_end_time=datetime.time(12, 0),
            start_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
            end_time=datetime.datetime(2024, 1, 1, 1, 0, tzinfo=datetime.timezone.utc),
            is_flow_completed=True,
            flow_activity_ids=None,
            flow_name=None,
        )

        data = entity.model_dump(mode="json", by_alias=True)
        assert "flowActivityIds" not in data, "flowActivityIds should be excluded when None"
        assert "flowName" not in data, "flowName should be excluded when None"

    def test_completed_entity_includes_flow_fields_when_present(self):
        """flowActivityIds and flowName should be included when populated."""
        activity_ids = [uuid.uuid4(), uuid.uuid4()]
        entity = CompletedEntity(
            id=f"{uuid.uuid4()}_1.0.0",
            answer_id=uuid.uuid4(),
            submit_id=uuid.uuid4(),
            version="1.0.0",
            local_end_date=datetime.date.today(),
            local_end_time=datetime.time(12, 0),
            start_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
            end_time=datetime.datetime(2024, 1, 1, 1, 0, tzinfo=datetime.timezone.utc),
            is_flow_completed=False,
            flow_activity_ids=activity_ids,
            flow_name="My Flow",
        )

        data = entity.model_dump(mode="json", by_alias=True)
        assert "flowActivityIds" in data, "flowActivityIds should be included when populated"
        assert data["flowActivityIds"] == [str(aid) for aid in activity_ids]
        assert "flowName" in data
        assert data["flowName"] == "My Flow"

    def test_completed_entity_datetime_serialization(self):
        """start_time and end_time should serialize to millisecond timestamps in JSON."""
        dt = datetime.datetime(2024, 6, 15, 10, 30, 0, tzinfo=datetime.timezone.utc)
        entity = CompletedEntity(
            id=f"{uuid.uuid4()}_1.0.0",
            answer_id=uuid.uuid4(),
            submit_id=uuid.uuid4(),
            version="1.0.0",
            local_end_date=datetime.date.today(),
            local_end_time=datetime.time(12, 0),
            start_time=dt,
            end_time=dt,
        )

        data = entity.model_dump(mode="json", by_alias=True)
        expected_ms = int(dt.timestamp() * 1000)
        assert data["startTime"] == expected_ms
        assert data["endTime"] == expected_ms

    def test_completed_entity_group_progress_id_unversioned(self):
        """group_progress_id should use unversioned flow UUID, not history ID."""
        flow_uuid = uuid.uuid4()
        event_id = str(uuid.uuid4())
        subject_id = uuid.uuid4()

        entity = CompletedEntity(
            id=f"{uuid.uuid4()}_1.0.0",
            answer_id=uuid.uuid4(),
            submit_id=uuid.uuid4(),
            version="1.0.0",
            flow_history_id=f"{flow_uuid}_1.0.0",
            local_end_date=datetime.date.today(),
            local_end_time=datetime.time(12, 0),
            start_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
            end_time=datetime.datetime(2024, 1, 1, 1, 0, tzinfo=datetime.timezone.utc),
            scheduled_event_id=event_id,
            target_subject_id=subject_id,
        )

        # group_progress_id should use unversioned flow_id
        gp_id = entity.group_progress_id
        assert gp_id == (flow_uuid, event_id, subject_id)

        # group_progress_history_id should use versioned flow_history_id
        gph_id = entity.group_progress_history_id
        assert gph_id == (f"{flow_uuid}_1.0.0", event_id, subject_id)
