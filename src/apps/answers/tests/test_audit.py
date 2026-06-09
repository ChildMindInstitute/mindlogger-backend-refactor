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
        assert event.curious_answer_id is not None
        assert answer.id in event.curious_answer_id

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
        assert event.curious_answer_id is not None
        assert tom_answer_activity_flow_audit.id in event.curious_answer_id

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
        assert event.curious_submit_id == [tom_answer_activity_flow_audit.submit_id]

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
        assert event.curious_submit_id == [missing_submit_id]

    # --- applet_answer_reviews_retrieve ---

    answer_reviews_url = "/answers/applet/{applet_id}/answers/{answer_id}/reviews"

    async def test_answer_reviews_retrieve_audit_success(
        self,
        client: TestClient,
        tom: User,
        answer_reviewable_activity: AnswerSchema,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        response = await client.get(
            self.answer_reviews_url.format(
                applet_id=answer_reviewable_activity.applet_id,
                answer_id=answer_reviewable_activity.id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_ASSESSMENT_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [answer_reviewable_activity.applet_id]
        assert event.curious_answer_id == [answer_reviewable_activity.id]

    async def test_answer_reviews_retrieve_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        missing_answer_id = uuid.uuid4()
        response = await client.get(
            self.answer_reviews_url.format(
                applet_id=missing_applet_id,
                answer_id=missing_answer_id,
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_ASSESSMENT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]
        assert event.curious_answer_id == [missing_answer_id]

    # --- applet_activity_assessment_retrieve ---

    activity_assessment_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment"

    async def test_activity_assessment_retrieve_audit_success(
        self,
        client: TestClient,
        tom: User,
        answer_reviewable_activity: AnswerSchema,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        response = await client.get(
            self.activity_assessment_url.format(
                applet_id=answer_reviewable_activity.applet_id,
                answer_id=answer_reviewable_activity.id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_ASSESSMENT_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [answer_reviewable_activity.applet_id]
        assert event.curious_answer_id == [answer_reviewable_activity.id]

    async def test_activity_assessment_retrieve_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        missing_answer_id = uuid.uuid4()
        response = await client.get(
            self.activity_assessment_url.format(
                applet_id=missing_applet_id,
                answer_id=missing_answer_id,
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_ASSESSMENT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]
        assert event.curious_answer_id == [missing_answer_id]

    # --- applet_submission_assessment_retrieve ---

    submission_assessment_url = "/answers/applet/{applet_id}/submissions/{submission_id}/assessments"

    async def test_submission_assessment_retrieve_audit_success(
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
            self.submission_assessment_url.format(
                applet_id=applet_with_flow.id,
                submission_id=tom_answer_activity_flow_audit.submit_id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_ASSESSMENT_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_with_flow.id]
        assert event.curious_submit_id == [tom_answer_activity_flow_audit.submit_id]

    async def test_submission_assessment_retrieve_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        missing_submission_id = uuid.uuid4()
        response = await client.get(
            self.submission_assessment_url.format(
                applet_id=missing_applet_id,
                submission_id=missing_submission_id,
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_ASSESSMENT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]
        assert event.curious_submit_id == [missing_submission_id]

    # --- applet_activity_identifiers_retrieve ---

    activity_identifiers_url = "/answers/applet/{applet_id}/summary/activities/{activity_id}/identifiers"

    async def test_activity_identifiers_retrieve_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        response = await client.get(
            self.activity_identifiers_url.format(
                applet_id=applet.id,
                activity_id=applet.activities[0].id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_IDENTIFIER_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet.id]

    async def test_activity_identifiers_retrieve_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        response = await client.get(
            self.activity_identifiers_url.format(
                applet_id=missing_applet_id,
                activity_id=uuid.uuid4(),
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_IDENTIFIER_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]

    # --- applet_flow_identifiers_retrieve ---

    flow_identifiers_url = "/answers/applet/{applet_id}/flows/{flow_id}/identifiers"

    async def test_flow_identifiers_retrieve_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet_with_flow: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        response = await client.get(
            self.flow_identifiers_url.format(
                applet_id=applet_with_flow.id,
                flow_id=applet_with_flow.activity_flows[0].id,
            ),
            dict(targetSubjectId=str(uuid.uuid4())),
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_IDENTIFIER_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_with_flow.id]

    async def test_flow_identifiers_retrieve_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        response = await client.get(
            self.flow_identifiers_url.format(
                applet_id=missing_applet_id,
                flow_id=uuid.uuid4(),
            ),
            dict(targetSubjectId=str(uuid.uuid4())),
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_IDENTIFIER_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]

    # --- applet_submission_reviews_retrieve ---

    submission_reviews_url = "/answers/applet/{applet_id}/submissions/{submission_id}/reviews"

    async def test_submission_reviews_retrieve_audit_success(
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
            self.submission_reviews_url.format(
                applet_id=applet_with_flow.id,
                submission_id=tom_answer_activity_flow_audit.submit_id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_ASSESSMENT_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_with_flow.id]
        assert event.curious_submit_id == [tom_answer_activity_flow_audit.submit_id]

    async def test_submission_reviews_retrieve_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        missing_submission_id = uuid.uuid4()
        response = await client.get(
            self.submission_reviews_url.format(
                applet_id=missing_applet_id,
                submission_id=missing_submission_id,
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_ASSESSMENT_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]
        assert event.curious_submit_id == [missing_submission_id]

    # --- answer_note_list ---

    answer_notes_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes"

    async def test_answer_note_list_audit_success(
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
            self.answer_notes_url.format(
                applet_id=applet.id,
                answer_id=answer.id,
                activity_id=applet.activities[0].id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_NOTE_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet.id]
        assert event.curious_answer_id == [answer.id]

    async def test_answer_note_list_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        missing_answer_id = uuid.uuid4()
        response = await client.get(
            self.answer_notes_url.format(
                applet_id=missing_applet_id,
                answer_id=missing_answer_id,
                activity_id=uuid.uuid4(),
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_NOTE_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]
        assert event.curious_answer_id == [missing_answer_id]

    # --- submission_note_list ---

    submission_notes_url = "/answers/applet/{applet_id}/submissions/{submission_id}/flows/{flow_id}/notes"

    async def test_submission_note_list_audit_success(
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
            self.submission_notes_url.format(
                applet_id=applet_with_flow.id,
                submission_id=tom_answer_activity_flow_audit.submit_id,
                flow_id=applet_with_flow.activity_flows[0].id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_NOTE_VIEW
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_with_flow.id]
        assert event.curious_submit_id == [tom_answer_activity_flow_audit.submit_id]

    async def test_submission_note_list_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        missing_submission_id = uuid.uuid4()
        response = await client.get(
            self.submission_notes_url.format(
                applet_id=missing_applet_id,
                submission_id=missing_submission_id,
                flow_id=uuid.uuid4(),
            )
        )

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_NOTE_VIEW
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]
        assert event.curious_submit_id == [missing_submission_id]

    # --- applet_answers_export ---

    answers_export_url = "/answers/applet/{applet_id}/data"

    async def test_answers_export_audit_success(
        self,
        client: TestClient,
        tom: User,
        applet: AppletFull,
        answer: AnswerSchema,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        response = await client.get(self.answers_export_url.format(applet_id=applet.id))

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_EXPORT
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet.id]
        assert answer.id in event.curious_answer_id

    async def test_answers_export_audit_failure(
        self,
        client: TestClient,
        tom: User,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.answers.api.log")
        client.login(tom)

        missing_applet_id = uuid.uuid4()
        response = await client.get(self.answers_export_url.format(applet_id=missing_applet_id))

        assert response.status_code != http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_EXPORT
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [missing_applet_id]
