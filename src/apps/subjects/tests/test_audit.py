import http
import uuid

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.domain.applet_full import AppletFull
from apps.audit import EventAction, EventOutcome
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject
from apps.users import User


@pytest.fixture
async def lucy_applet_one_subject(session: AsyncSession, lucy: User, applet_one_lucy_respondent: AppletFull) -> Subject:
    query = select(SubjectSchema).where(
        SubjectSchema.user_id == lucy.id,
        SubjectSchema.applet_id == applet_one_lucy_respondent.id,
    )
    res = await session.execute(query, execution_options={"synchronize_session": False})
    return Subject.model_validate(res.scalars().one())


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

    async def test_delete_subject_audit_success(
        self,
        client: TestClient,
        tom: User,
        lucy: User,
        lucy_applet_one_subject: Subject,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.subjects.api.log")
        client.login(tom)

        response = await client.delete(
            self.subject_detail_url.format(subject_id=lucy_applet_one_subject.id),
            data={"delete_answers": False},
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.WORKSPACE_ACCESS_REVOKE
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.user_target_id == lucy.id
        assert event.curious_applet_id == [lucy_applet_one_subject.applet_id]
        assert event.curious_subject_id == [lucy_applet_one_subject.id]

    async def test_delete_subject_audit_failure_403(
        self,
        client: TestClient,
        tom: User,
        lucy: User,
        tom_applet_one_subject: Subject,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.subjects.api.log")
        client.login(lucy)

        response = await client.delete(
            self.subject_detail_url.format(subject_id=tom_applet_one_subject.id),
            data={"delete_answers": False},
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN, response.json()
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == lucy.id
        assert event.event_action == EventAction.WORKSPACE_ACCESS_REVOKE
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [tom_applet_one_subject.applet_id]
        assert event.curious_subject_id == [tom_applet_one_subject.id]

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
