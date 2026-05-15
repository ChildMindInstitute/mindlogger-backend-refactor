import http
import uuid

from pytest_mock import MockerFixture

from apps.applets.domain.applet_full import AppletFull
from apps.audit import EventAction, EventOutcome
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.domain import Subject
from apps.users import User


class TestWorkspacesAudit(BaseTest):
    fixtures = [
        "folders/fixtures/folders.json",
        "invitations/fixtures/invitations.json",
        "workspaces/fixtures/workspaces.json",
        "folders/fixtures/folders_applet.json",
    ]

    workspace_respondents_url = "/workspaces/{owner_id}/respondents"
    workspace_applet_respondents_list = "/workspaces/{owner_id}/applets/{applet_id}/respondents"
    workspace_get_applet_respondent = "/workspaces/{owner_id}/applets/{applet_id}/respondents/{respondent_id}"

    async def test_workspace_respondents_list_audit_success_emits_event_per_applet(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        applet_two: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.workspaces.api.log")
        client.login(tom)

        response = await client.get(self.workspace_respondents_url.format(owner_id=tom.id))

        assert response.status_code == http.HTTPStatus.OK
        assert audit_log.await_count >= 1
        events = [call.args[0] for call in audit_log.call_args_list]
        for event in events:
            assert event.user_id == tom.id
            assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
            assert event.event_outcome == EventOutcome.SUCCESS
            assert event.curious_applet_id is not None
            assert len(event.curious_applet_id) == 1

        applet_ids = {event.curious_applet_id[0] for event in events}
        assert applet_one.id in applet_ids
        assert applet_two.id in applet_ids

    async def test_workspace_respondents_list_audit_failure_single_event(
        self,
        client: TestClient,
        lucy: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.workspaces.api.log")
        client.login(lucy)

        missing_owner_id = uuid.uuid4()
        response = await client.get(self.workspace_respondents_url.format(owner_id=missing_owner_id))

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == lucy.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE

    async def test_workspace_applet_respondents_list_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.workspaces.api.log")
        client.login(tom)

        response = await client.get(
            self.workspace_applet_respondents_list.format(owner_id=tom.id, applet_id=applet_one.id)
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_one.id]

    async def test_workspace_applet_respondents_list_audit_failure(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.workspaces.api.log")
        client.login(tom)

        missing_owner_id = uuid.uuid4()
        response = await client.get(
            self.workspace_applet_respondents_list.format(owner_id=missing_owner_id, applet_id=applet_one.id)
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [applet_one.id]

    async def test_workspace_applet_get_respondent_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        tom_applet_one_subject: Subject,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.workspaces.api.log")
        client.login(tom)

        response = await client.get(
            self.workspace_get_applet_respondent.format(owner_id=tom.id, applet_id=applet_one.id, respondent_id=tom.id)
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_one.id]
        assert event.curious_subject_id == [tom_applet_one_subject.id]

    async def test_workspace_applet_get_respondent_audit_failure(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.workspaces.api.log")
        client.login(tom)

        missing_respondent_id = uuid.uuid4()
        response = await client.get(
            self.workspace_get_applet_respondent.format(
                owner_id=tom.id, applet_id=applet_one.id, respondent_id=missing_respondent_id
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [applet_one.id]
