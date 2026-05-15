import datetime
import http
import uuid

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.db.schemas import AnswerSchema
from apps.answers.domain import ClientMeta
from apps.answers.domain.answers import AppletAnswerCreate, ItemAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain.applet_full import AppletFull
from apps.audit import EventAction, EventOutcome
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User


@pytest.fixture
async def tom_answer_activity_flow_audit(
    session: AsyncSession, tom: User, applet_with_flow: AppletFull
) -> AnswerSchema:
    answer_service = AnswerService(session, tom.id)
    return await answer_service.create_answer(
        AppletAnswerCreate(
            applet_id=applet_with_flow.id,
            version=applet_with_flow.version,
            submit_id=uuid.uuid4(),
            flow_id=applet_with_flow.activity_flows[0].id,
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                start_time=datetime.datetime.now(datetime.UTC),
                end_time=datetime.datetime.now(datetime.UTC),
                user_public_key=str(tom.id),
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
            consent_to_share=False,
        )
    )


class TestAnswersAudit(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]

    activity_answers_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers"
    flow_submissions_url = "/answers/applet/{applet_id}/flows/{flow_id}/submissions"
    activity_answer_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{answer_id}"
    flow_submission_url = "/answers/applet/{applet_id}/flows/{flow_id}/submissions/{submit_id}"

    # --- applet_activity_answers_list ---

    async def test_activity_answers_list_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet: AppletFull,
        answer: AnswerSchema,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        response = await client.get(
            self.activity_answers_url.format(
                applet_id=applet.id,
                activity_id=applet.activities[0].id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet.id]

    async def test_activity_answers_list_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        response = await client.get(
            self.activity_answers_url.format(
                applet_id=missing_applet_id,
                activity_id=uuid.uuid4(),
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]

    # --- applet_flow_submissions_list ---

    async def test_flow_submissions_list_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow_audit: AnswerSchema,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        response = await client.get(
            self.flow_submissions_url.format(
                applet_id=applet_with_flow.id,
                flow_id=applet_with_flow.activity_flows[0].id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_with_flow.id]

    async def test_flow_submissions_list_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        response = await client.get(
            self.flow_submissions_url.format(
                applet_id=missing_applet_id,
                flow_id=uuid.uuid4(),
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]

    # --- applet_activity_answer_retrieve ---

    async def test_activity_answer_retrieve_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet: AppletFull,
        answer: AnswerSchema,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        response = await client.get(
            self.activity_answer_url.format(
                applet_id=applet.id,
                activity_id=applet.activities[0].id,
                answer_id=answer.id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet.id]
        assert event.curious_answer_id == [answer.id]

    async def test_activity_answer_retrieve_audit_failure(
        self,
        client: TestClient,
        tom: User,
        applet: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_answer_id = uuid.uuid4()
        response = await client.get(
            self.activity_answer_url.format(
                applet_id=applet.id,
                activity_id=applet.activities[0].id,
                answer_id=missing_answer_id,
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [applet.id]
        assert event.curious_answer_id == [missing_answer_id]

    # --- applet_flow_answer_retrieve ---

    async def test_flow_answer_retrieve_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow_audit: AnswerSchema,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        response = await client.get(
            self.flow_submission_url.format(
                applet_id=applet_with_flow.id,
                flow_id=applet_with_flow.activity_flows[0].id,
                submit_id=tom_answer_activity_flow_audit.submit_id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_with_flow.id]
        assert event.curious_answer_id == [tom_answer_activity_flow_audit.submit_id]

    async def test_flow_answer_retrieve_audit_failure(
        self,
        client: TestClient,
        tom: User,
        applet_with_flow: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_submit_id = uuid.uuid4()
        response = await client.get(
            self.flow_submission_url.format(
                applet_id=applet_with_flow.id,
                flow_id=applet_with_flow.activity_flows[0].id,
                submit_id=missing_submit_id,
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [applet_with_flow.id]
        assert event.curious_answer_id == [missing_submit_id]
