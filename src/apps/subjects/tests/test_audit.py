import http
import uuid

from pytest_mock import MockerFixture

from apps.applets.domain.applet_full import AppletFull
from apps.audit import EventAction, EventOutcome
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.domain import Subject
from apps.users import User


class TestSubjectsAudit(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]

    my_subject_url = "/users/me/subjects/{applet_id}"
    subject_detail_url = "/subjects/{subject_id}"
    subject_target_by_respondent_url = (
        "/subjects/respondent/{respondent_subject_id}/activity-or-flow/{activity_or_flow_id}"
    )

    async def test_get_subject_audit_success(
        self,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: Subject,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.subjects.api.log")
        client.login(tom)

        response = await client.get(self.subject_detail_url.format(subject_id=tom_applet_one_subject.id))

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [tom_applet_one_subject.applet_id]
        assert event.curious_subject_id == [tom_applet_one_subject.id]

    async def test_get_subject_audit_failure_not_found(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.subjects.api.log")
        client.login(tom)

        missing_subject_id = uuid.uuid4()
        response = await client.get(self.subject_detail_url.format(subject_id=missing_subject_id))

        assert response.status_code == http.HTTPStatus.NOT_FOUND
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_subject_id == [missing_subject_id]

    async def test_get_my_subject_audit_success(
        self,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: Subject,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.subjects.api.log")
        client.login(tom)

        response = await client.get(self.my_subject_url.format(applet_id=tom_applet_one_subject.applet_id))

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [tom_applet_one_subject.applet_id]
        assert event.curious_subject_id == [tom_applet_one_subject.id]

    async def test_get_my_subject_audit_failure_invalid_applet(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.subjects.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        response = await client.get(self.my_subject_url.format(applet_id=missing_applet_id))

        assert response.status_code == http.HTTPStatus.NOT_FOUND
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]

    async def test_get_target_subjects_by_respondent_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        tom_applet_one_subject: Subject,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.subjects.api.log")
        client.login(tom)

        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=tom_applet_one_subject.id,
            activity_or_flow_id=applet_one.activities[0].id,
        )
        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [tom_applet_one_subject.applet_id]
        assert event.curious_subject_id is not None
        assert tom_applet_one_subject.id in event.curious_subject_id

    async def test_get_target_subjects_by_respondent_audit_failure_invalid_respondent(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.subjects.api.log")
        client.login(tom)

        missing_respondent_subject_id = uuid.uuid4()
        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=missing_respondent_subject_id,
            activity_or_flow_id=applet_one.activities[0].id,
        )
        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.NOT_FOUND
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_SUBJECT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_subject_id == [missing_respondent_subject_id]
