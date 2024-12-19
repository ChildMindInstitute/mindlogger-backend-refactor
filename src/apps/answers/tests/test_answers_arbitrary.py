import datetime
import http
import uuid
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from pytest import FixtureRequest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.answers.crud import AnswerItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.db.schemas import AnswerItemSchema, AnswerNoteSchema, AnswerSchema
from apps.answers.domain import AnswerNote, AppletAnswerCreate, AssessmentAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain.applet_full import AppletFull
from apps.applets.errors import InvalidVersionError
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.domain import Subject
from apps.subjects.services import SubjectsService
from apps.users.domain import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema, UserWorkspaceSchema
from apps.workspaces.domain.constants import Role
from infrastructure.utility import RedisCacheTest


def note_url_path_data(answer: AnswerSchema) -> dict[str, Any]:
    return {
        "applet_id": answer.applet_id,
        "answer_id": answer.id,
        "activity_id": answer.activity_history_id.split("_")[0],
    }


# This id is getting from JSON fixtures for answers
WORKSPACE_ARBITRARY_ID = uuid.UUID("8b83d791-0d27-42c5-8b1d-e0c8d7faf808")


async def set_db_uri(db_uri: str, session: AsyncSession):
    query: Query = update(UserWorkspaceSchema)
    query = query.where(UserWorkspaceSchema.id == WORKSPACE_ARBITRARY_ID)
    query = query.values(database_uri=db_uri)
    await session.execute(query)


async def get_answer_by_submit_id(submit_id: uuid.UUID, session: AsyncSession) -> AnswerSchema | None:
    query: Query = select(AnswerSchema)
    query = query.filter(AnswerSchema.submit_id == submit_id)
    result = await session.execute(query)
    return result.scalars().all()


async def assert_answer_exist_on_arbitrary(submit_id: str, session: AsyncSession):
    answer = await get_answer_by_submit_id(uuid.UUID(submit_id), session)
    assert answer


async def assert_answer_not_exist_on_arbitrary(submit_id: str, session: AsyncSession):
    answer = await get_answer_by_submit_id(uuid.UUID(submit_id), session)
    assert not answer


@pytest.fixture
async def lucy_manager_in_applet_with_reviewable_flow(session, tom, lucy, applet_with_reviewable_flow) -> User:
    await UserAppletAccessCRUD(session).save(
        UserAppletAccessSchema(
            user_id=lucy.id,
            applet_id=applet_with_reviewable_flow.id,
            role=Role.MANAGER,
            owner_id=tom.id,
            invitor_id=tom.id,
            meta=dict(),
            nickname=str(uuid.uuid4()),
        )
    )
    return lucy


@pytest.fixture
async def submission_assessment_answer(
    tom: User,
    session: AsyncSession,
    arbitrary_session: AsyncSession,
    assessment_submission_create: AssessmentAnswerCreate,
    applet_with_reviewable_flow: AppletFull,
) -> AnswerItemSchema | None:
    service = AnswerService(session, tom.id, arbitrary_session)
    assert assessment_submission_create.reviewed_flow_submit_id
    answer = await service.get_submission_last_answer(assessment_submission_create.reviewed_flow_submit_id)
    assert answer
    submission_id = assessment_submission_create.reviewed_flow_submit_id
    assert submission_id
    await service.create_assessment_answer(
        applet_with_reviewable_flow.id, answer.id, assessment_submission_create, submission_id
    )
    return await AnswerItemsCRUD(arbitrary_session).get_assessment(answer.id, tom.id)


@pytest.mark.usefixtures("mock_kiq_report")
class TestAnswerActivityItems(BaseTest):
    fixtures = ["answers/fixtures/arbitrary_server_answers.json"]
    login_url = "/auth/login"
    answer_url = "/answers"
    public_answer_url = "/public/answers"

    review_activities_url = "/answers/applet/{applet_id}/review/activities"

    summary_activities_url = "/answers/applet/{applet_id}/summary/activities"
    identifiers_url = f"{summary_activities_url}/{{activity_id}}/identifiers"
    versions_url = f"{summary_activities_url}/{{activity_id}}/versions"

    answers_for_activity_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers"
    applet_answers_export_url = "/answers/applet/{applet_id}/data"
    applet_submit_dates_url = "/answers/applet/{applet_id}/dates"

    activity_answers_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{answer_id}"
    assessment_answers_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment"

    answer_reviews_url = "/answers/applet/{applet_id}/answers/{answer_id}/reviews"
    answer_notes_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes"
    answer_note_detail_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes/{note_id}"
    latest_report_url = "/answers/applet/{applet_id}/activities/{activity_id}/subjects/{subject_id}/latest_report"

    arbitrary_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_arbitrary"
    applet_answers_completions_url = "/answers/applet/{applet_id}/completions"
    applets_answers_completions_url = "/answers/applet/completions"
    check_existence_url = "/answers/check-existence"
    assessment_delete_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment/{assessment_id}"

    assessment_submissions_url = "/answers/applet/{applet_id}/submissions/{submission_id}/assessments"
    assessment_submissions_retrieve_url = "/answers/applet/{applet_id}/submissions/{submission_id}/assessments"
    assessment_submission_delete_url = (
        "/answers/applet/{applet_id}/submissions/{submission_id}/assessments/{assessment_id}"
    )

    async def test_answer_activity_items_create_for_respondent(
        self,
        mock_kiq_report: AsyncMock,
        arbitrary_client: TestClient,
        tom: User,
        redis: RedisCacheTest,
        answer_with_alert_create: AppletAnswerCreate,
        mailbox: TestMail,
        session: AsyncSession,
    ):
        arbitrary_client.login(tom)
        response = await arbitrary_client.post(self.answer_url, data=answer_with_alert_create)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        mock_kiq_report.assert_awaited_once()

        published_values = await redis.get(f"channel_{tom.id}")
        published_values = published_values or []
        assert len(published_values) == 1
        # 2 because alert for lucy and for tom
        assert len(redis._storage) == 1
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].subject == "Response alert"

        # TODO: Fix greenlet error and use fixture instead
        subject = await SubjectsService(session, tom.id).get_by_user_and_applet(
            tom.id, answer_with_alert_create.applet_id
        )
        assert subject
        response = await arbitrary_client.get(
            self.review_activities_url.format(applet_id=str(answer_with_alert_create.applet_id)),
            dict(
                targetSubjectId=subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await arbitrary_client.get(
            self.assessment_answers_url.format(
                applet_id=str(answer_with_alert_create.applet_id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()

    async def test_create_answer__wrong_applet_version(
        self,
        arbitrary_client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        arbitrary_client.login(tom)
        data = answer_create.copy(deep=True)
        data.version = "0.0.0"
        response = await arbitrary_client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == InvalidVersionError.message

    @pytest.mark.usefixtures("mock_report_server_response", "answer_arbitrary")
    async def test_get_latest_summary(
        self,
        arbitrary_session: AsyncSession,
        arbitrary_client: TestClient,
        tom: User,
        applet: AppletFull,
        tom_applet_subject: Subject,
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.post(
            self.latest_report_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
                subject_id=str(tom_applet_subject.id),
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.content == b"pdf body"
        response = await arbitrary_client.post(
            self.latest_report_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
                subject_id=str(uuid.uuid4()),
            ),
        )
        assert response.status_code == 404

    async def test_public_answer_activity_items_create_for_respondent(
        self, arbitrary_session: AsyncSession, arbitrary_client: TestClient, public_answer_create: AppletAnswerCreate
    ):
        response = await arbitrary_client.post(self.public_answer_url, data=public_answer_create)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(str(public_answer_create.submit_id), arbitrary_session)

    async def test_answer_skippable_activity_items_create_for_respondent(
        self,
        arbitrary_session: AsyncSession,
        arbitrary_client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet: AppletFull,
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await arbitrary_client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
                activityOrFlowId=applet.activities[0].id,
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]["dates"]) == 1
        await assert_answer_exist_on_arbitrary(str(answer_create.submit_id), arbitrary_session)

    async def test_answer_skippable_activity_items_create_for_respondent_with_flow_id(
        self,
        arbitrary_session: AsyncSession,
        arbitrary_client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet: AppletFull,
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await arbitrary_client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
                activityOrFlowId=applet.activity_flows[0].id,
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]["dates"]) == 1
        await assert_answer_exist_on_arbitrary(str(answer_create.submit_id), arbitrary_session)

    async def test_list_submit_dates_with_flow_id(
        self,
        arbitrary_session: AsyncSession,
        arbitrary_client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet: AppletFull,
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await arbitrary_client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
                activityOrFlowId=applet.activity_flows[0].id,
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]["dates"]) == 1
        await assert_answer_exist_on_arbitrary(str(answer_create.submit_id), arbitrary_session)

        response = await arbitrary_client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
                activityOrFlowId=applet.activity_flows[0].id,
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    async def test_list_submit_dates(
        self,
        arbitrary_session: AsyncSession,
        arbitrary_client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet: AppletFull,
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await arbitrary_client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
                activityOrFlowId=applet.activities[0].id,
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]["dates"]) == 1
        await assert_answer_exist_on_arbitrary(str(answer_create.submit_id), arbitrary_session)

        response = await arbitrary_client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
                activityOrFlowId=applet.activities[0].id,
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    async def test_answer_flow_items_create_for_respondent(
        self,
        arbitrary_session: AsyncSession,
        arbitrary_client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED
        await assert_answer_exist_on_arbitrary(str(answer_create.submit_id), arbitrary_session)

    async def test_answer_with_skipping_all(
        self,
        arbitrary_session: AsyncSession,
        arbitrary_client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        arbitrary_client.login(tom)
        response = await arbitrary_client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED
        await assert_answer_exist_on_arbitrary(str(answer_create.submit_id), arbitrary_session)

    async def test_answered_applet_activities(
        self,
        arbitrary_session: AsyncSession,
        arbitrary_client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        session: AsyncSession,
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED
        # TODO: Fix greenlet error and use fixture instead
        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, answer_create.applet_id)
        assert tom_subject
        response = await arbitrary_client.get(
            self.review_activities_url.format(applet_id=str(answer_create.applet_id)),
            dict(
                targetSubjectId=tom_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await arbitrary_client.get(
            self.activity_answers_url.format(
                applet_id=str(answer_create.applet_id),
                answer_id=answer_id,
                activity_id=str(answer_create.activity_id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["answer"]["events"] == answer_create.answer.events
        await assert_answer_exist_on_arbitrary(str(answer_create.submit_id), arbitrary_session)

        response = await arbitrary_client.get(
            self.review_activities_url.format(applet_id=str(answer_create.applet_id)),
            dict(
                targetSubjectId=tom_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await arbitrary_client.get(
            self.activity_answers_url.format(
                applet_id=str(answer_create.applet_id),
                answer_id=answer_id,
                activity_id=str(answer_create.activity_id),
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["answer"]["events"] == answer_create.answer.events

    async def test_fail_answered_applet_not_existed_activities(
        self,
        arbitrary_client: TestClient,
        tom: User,
        applet: AppletFull,
        uuid_zero: uuid.UUID,
        answer_arbitrary: AnswerSchema,
    ):
        arbitrary_client.login(tom)
        response = await arbitrary_client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_arbitrary.id,
                activity_id=uuid_zero,
            )
        )
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_applet_activity_answers(
        self, arbitrary_client: TestClient, tom: User, applet: AppletFull, answer_arbitrary: AnswerSchema
    ):
        arbitrary_client.login(tom)
        response = await arbitrary_client.get(
            self.answers_for_activity_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1

    async def test_applet_assessment_retrieve(
        self, arbitrary_client: TestClient, tom: User, answer_reviewable_activity_arbitrary: AnswerSchema
    ):
        arbitrary_client.login(tom)
        response = await arbitrary_client.get(
            self.assessment_answers_url.format(
                applet_id=str(answer_reviewable_activity_arbitrary.applet_id),
                answer_id=answer_reviewable_activity_arbitrary.id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]

    async def test_applet_assessment_create(
        self,
        arbitrary_client: TestClient,
        tom: User,
        assessment_arbitrary_create: AssessmentAnswerCreate,
        answer_reviewable_activity_arbitrary: AnswerSchema,
        applet_with_reviewable_activity: AppletFull,
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.post(
            self.assessment_answers_url.format(
                applet_id=str(answer_reviewable_activity_arbitrary.applet_id),
                answer_id=answer_reviewable_activity_arbitrary.id,
            ),
            data=assessment_arbitrary_create,
        )

        assert response.status_code == http.HTTPStatus.CREATED
        review_activity = next(i for i in applet_with_reviewable_activity.activities if i.is_reviewable)
        general_activity = next(i for i in applet_with_reviewable_activity.activities if not i.is_reviewable)

        response = await arbitrary_client.get(
            self.assessment_answers_url.format(
                applet_id=str(answer_reviewable_activity_arbitrary.applet_id),
                answer_id=answer_reviewable_activity_arbitrary.id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        assessment = response.json()["result"]
        assert assessment["answer"] == assessment_arbitrary_create.answer
        assert assessment["reviewerPublicKey"] == assessment_arbitrary_create.reviewer_public_key
        assert assessment["itemIds"] == [str(i) for i in assessment_arbitrary_create.item_ids]
        assert assessment["versions"] == [
            f"{general_activity.id}_{applet_with_reviewable_activity.version}",
            f"{review_activity.id}_{applet_with_reviewable_activity.version}",
        ]
        assert not assessment["itemsLast"] == general_activity.dict()["items"][0]
        assert not assessment["items"]

    @pytest.mark.usefixtures("assessment_arbitrary")
    async def test_get_review_assessment(
        self,
        arbitrary_client: TestClient,
        tom: User,
        answer_reviewable_activity_arbitrary: AnswerSchema,
        assessment_arbitrary_create: AssessmentAnswerCreate,
    ):
        arbitrary_client.login(tom)
        response = await arbitrary_client.get(
            self.answer_reviews_url.format(
                applet_id=str(answer_reviewable_activity_arbitrary.applet_id),
                answer_id=answer_reviewable_activity_arbitrary.id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        review = response.json()["result"][0]
        assert review["answer"] == assessment_arbitrary_create.answer
        assert review["reviewerPublicKey"] == assessment_arbitrary_create.reviewer_public_key
        assert review["itemIds"] == [str(i) for i in assessment_arbitrary_create.item_ids]
        assert review["reviewer"]["firstName"] == tom.first_name
        assert review["reviewer"]["lastName"] == tom.last_name

    async def test_applet_activities(
        self, arbitrary_client: TestClient, tom: User, answer_arbitrary: AnswerSchema, tom_applet_subject: Subject
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.get(
            self.review_activities_url.format(applet_id=str(answer_arbitrary.applet_id)),
            dict(
                targetSubjectId=tom_applet_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

    async def test_add_note(
        self, arbitrary_client: TestClient, tom: User, answer_arbitrary: AnswerSchema, note_create_data: AnswerNote
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.post(
            self.answer_notes_url.format(**note_url_path_data(answer_arbitrary)), data=note_create_data
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await arbitrary_client.get(self.answer_notes_url.format(**note_url_path_data(answer_arbitrary)))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        note = response.json()["result"][0]
        assert note["note"] == note_create_data.note
        assert note["user"]["firstName"] == tom.first_name
        assert note["user"]["lastName"] == tom.last_name
        # Just check that other columns in place
        assert note["id"]
        assert note["createdAt"]

    async def test_edit_note(
        self,
        arbitrary_client: TestClient,
        tom: User,
        answer_arbitrary: AnswerSchema,
        answer_note_arbitrary: AnswerNoteSchema,
    ):
        arbitrary_client.login(tom)

        note_new = answer_note_arbitrary.note + "new"

        response = await arbitrary_client.put(
            self.answer_note_detail_url.format(
                **note_url_path_data(answer_arbitrary), note_id=answer_note_arbitrary.id
            ),
            dict(note=note_new),
        )
        assert response.status_code == http.HTTPStatus.OK

        response = await arbitrary_client.get(self.answer_notes_url.format(**note_url_path_data(answer_arbitrary)))

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == note_new

    async def test_delete_note(
        self, arbitrary_client: TestClient, tom: User, answer_arbitrary: AnswerSchema, answer_note: AnswerNoteSchema
    ):
        arbitrary_client.login(tom)
        note_id = answer_note.id

        response = await arbitrary_client.delete(
            self.answer_note_detail_url.format(**note_url_path_data(answer_arbitrary), note_id=note_id)
        )
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        response = await arbitrary_client.get(self.answer_notes_url.format(**note_url_path_data(answer_arbitrary)))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 0

    async def test_answer_activity_items_create_for_not_respondent(
        self, arbitrary_client: TestClient, user: User, answer_create: AppletAnswerCreate
    ):
        arbitrary_client.login(user)
        response = await arbitrary_client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    @pytest.mark.usefixtures("assessment_arbitrary")
    async def test_answers_export(
        self,
        arbitrary_client: TestClient,
        tom: User,
        answer_reviewable_activity_arbitrary: AnswerSchema,
    ):
        arbitrary_client.login(tom)
        response = await arbitrary_client.get(
            self.applet_answers_export_url.format(
                applet_id=str(answer_reviewable_activity_arbitrary.applet_id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        resp_data = response.json()
        data = resp_data["result"]
        assert set(data.keys()) == {"answers", "activities"}
        assert len(data["answers"]) == 2
        assert resp_data["count"] == 2

        assessment, answer = data["answers"][0], data["answers"][1]
        # fmt: off
        expected_keys = {
            "activityHistoryId", "activityId", "answer", "appletHistoryId",
            "appletId", "createdAt", "events", "flowHistoryId", "flowId",
            "flowName", "id", "itemIds", "migratedData", "respondentId",
            "respondentSecretId", "reviewedAnswerId", "userPublicKey",
            "version", "submitId", "scheduledDatetime", "startDatetime",
            "endDatetime", "legacyProfileId", "migratedDate", "relation",
            "sourceSubjectId", "sourceSecretId", "sourceUserNickname", "sourceUserTag",
            "targetSubjectId", "targetSecretId", "targetUserNickname", "targetUserTag",
            "inputSubjectId", "inputSecretId", "inputUserNickname",
            "client", "tzOffset", "scheduledEventId", "reviewedFlowSubmitId"
        }

        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer["id"]

    @pytest.mark.parametrize(
        "user_fixture, exp_cnt",
        (("lucy", 0), ("tom", 1)),
    )
    async def test_get_applet_answers_export_filter_by_respondent_id(
        self,
        arbitrary_client: TestClient,
        tom: User,
        answer_arbitrary: AnswerSchema,
        request: FixtureRequest,
        user_fixture: str,
        exp_cnt: int,
    ):
        arbitrary_client.login(tom)
        respondent: User = request.getfixturevalue(user_fixture)
        response = await arbitrary_client.get(
            self.applet_answers_export_url.format(
                applet_id=str(answer_arbitrary.applet_id),
            ),
            dict(respondentIds=str(respondent.id)),
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == exp_cnt
        assert len(response.json()["result"]["answers"]) == exp_cnt

    async def test_get_identifiers(
        self, arbitrary_client: TestClient, tom: User, answer_create: AppletAnswerCreate, applet: AppletFull
    ):
        arbitrary_client.login(tom)
        identifier_url = self.identifiers_url.format(applet_id=str(applet.id), activity_id=str(applet.activities[0].id))
        identifier_url = f"{identifier_url}?respondentId={tom.id}"
        response = await arbitrary_client.get(identifier_url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 0

        created_at = datetime.datetime.utcnow()
        data = answer_create.copy(deep=True)
        data.created_at = created_at

        response = await arbitrary_client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED
        response = await arbitrary_client.get(identifier_url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["identifier"] == answer_create.answer.identifier
        assert response.json()["result"][0]["userPublicKey"] == answer_create.answer.user_public_key
        assert datetime.datetime.fromisoformat(response.json()["result"][0]["lastAnswerDate"]) == created_at

    async def test_get_all_activity_versions_for_applet(
        self, arbitrary_client: TestClient, tom: User, applet: AppletFull
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.get(
            self.versions_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["version"] == applet.version
        assert response.json()["result"][0]["createdAt"]

    async def test_get_summary_activities_no_answer_no_performance_task(
        self, arbitrary_client: TestClient, tom: User, applet: AppletFull
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == applet.activities[0].name
        assert response.json()["result"][0]["id"] == str(applet.activities[0].id)
        assert not response.json()["result"][0]["isPerformanceTask"]
        assert not response.json()["result"][0]["hasAnswer"]

    @pytest.mark.usefixtures("answer_arbitrary")
    async def test_get_summary_activities_has_answer_no_performance_task(
        self, arbitrary_client: TestClient, tom: User, applet: AppletFull
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        activity = response.json()["result"][0]
        assert activity["name"] == applet.activities[0].name
        assert activity["id"] == str(applet.activities[0].id)
        assert not activity["isPerformanceTask"]
        assert activity["hasAnswer"]

    async def test_store_client_meta(
        self,
        arbitrary_client: TestClient,
        arbitrary_session: AsyncSession,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        arbitrary_client.login(tom)
        response = await arbitrary_client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

        db_result = await arbitrary_session.execute(select(AnswerSchema))
        res: AnswerSchema = db_result.scalars().first()
        assert res.client["app_id"] == answer_create.client.app_id
        assert res.client["app_version"] == answer_create.client.app_version
        assert res.client["width"] == answer_create.client.width
        assert res.client["height"] == answer_create.client.height

    async def test_activity_answers_by_identifier(
        self, arbitrary_client: TestClient, tom: User, answer_arbitrary: AnswerSchema, answer_create: AppletAnswerCreate
    ):
        arbitrary_client.login(tom)

        response = await arbitrary_client.get(
            self.answers_for_activity_url.format(
                applet_id=str(answer_create.applet_id),
                activity_id=str(answer_create.activity_id),
            ),
            query={"emptyIdentifiers": False, "identifiers": answer_create.answer.identifier},
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()
        assert result["count"] == 1
        assert result["result"][0]["answerId"] == str(answer_arbitrary.id)

    async def test_applet_completions(
        self, arbitrary_client: TestClient, tom: User, answer_arbitrary: AnswerSchema, answer_create: AppletAnswerCreate
    ):
        arbitrary_client.login(tom)
        answer_create.answer.local_end_date = cast(datetime.date, answer_create.answer.local_end_date)
        answer_create.answer.local_end_time = cast(datetime.time, answer_create.answer.local_end_time)
        response = await arbitrary_client.get(
            self.applet_answers_completions_url.format(
                applet_id=str(answer_arbitrary.applet_id),
            ),
            {"fromDate": answer_create.answer.local_end_date.isoformat(), "version": answer_arbitrary.version},
        )

        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]
        assert set(data.keys()) == {
            "id",
            "version",
            "activities",
            "activityFlows",
        }
        assert len(data["activities"]) == 1
        activity_answer_data = data["activities"][0]
        assert set(activity_answer_data.keys()) == {
            "id",
            "answerId",
            "submitId",
            "targetSubjectId",
            "scheduledEventId",
            "localEndDate",
            "localEndTime",
        }
        assert activity_answer_data["answerId"] == str(answer_arbitrary.id)
        assert activity_answer_data["localEndTime"] == str(answer_create.answer.local_end_time)

    async def test_applets_completions(
        self,
        arbitrary_client: TestClient,
        tom: User,
        answer_arbitrary: AnswerSchema,
        answer_create: AppletAnswerCreate,
        session: AsyncSession,
        arbitrary_db_url: str,
    ):
        arbitrary_client.login(tom)
        # Just for this test, because in json fixtures we have hardcoded encrypted localhost. And it does not work
        # in container
        await set_db_uri(arbitrary_db_url, session)
        answer_create.answer.local_end_date = cast(datetime.date, answer_create.answer.local_end_date)
        answer_create.answer.local_end_time = cast(datetime.time, answer_create.answer.local_end_time)
        # test completions
        response = await arbitrary_client.get(
            url=self.applets_answers_completions_url,
            query={"fromDate": answer_create.answer.local_end_date.isoformat()},
        )

        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]
        # 2 session applets and 1 for answers
        assert len(data) == 3
        applet_with_answer = next(i for i in data if i["id"] == str(answer_arbitrary.applet_id))

        assert applet_with_answer["id"] == str(answer_arbitrary.applet_id)
        assert applet_with_answer["version"] == answer_arbitrary.version

    async def test_check_existance_answer_exists(
        self, arbitrary_client: TestClient, tom: User, answer_arbitrary: AnswerSchema
    ):
        arbitrary_client.login(tom)
        data = {
            "applet_id": str(answer_arbitrary.applet_id),
            "activity_id": answer_arbitrary.activity_history_id.split("_")[0],
            # On backend we devide on 1000
            "created_at": answer_arbitrary.created_at.timestamp() * 1000,
        }
        resp = await arbitrary_client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["exists"]

    @pytest.mark.parametrize(
        "column,value",
        (
            ("activity_id", "00000000-0000-0000-0000-000000000000_99"),
            ("created_at", datetime.datetime.utcnow().timestamp() * 1000),
        ),
    )
    async def test_check_existance_answer_does_not_exist(
        self, arbitrary_client: TestClient, tom: User, answer_arbitrary: AnswerSchema, column: str, value: str
    ):
        arbitrary_client.login(tom)
        data = {
            "applet_id": str(answer_arbitrary.applet_id),
            "activity_id": answer_arbitrary.activity_history_id.split("_")[0],
            "created_at": answer_arbitrary.created_at.timestamp(),
        }
        data[column] = value
        resp = await arbitrary_client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]["exists"]

    async def test_check_existance_answer_does_not_exist__not_answer_applet(
        self, arbitrary_client: TestClient, tom: User, answer_arbitrary: AnswerSchema, applet_one: AppletFull
    ):
        arbitrary_client.login(tom)
        data = {
            "applet_id": str(applet_one.id),
            "activity_id": answer_arbitrary.activity_history_id.split("_")[0],
            "created_at": answer_arbitrary.created_at.timestamp(),
        }
        resp = await arbitrary_client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]["exists"]

    async def test_own_review_delete(
        self,
        tom_answer_create_data,
        tom_answer_assessment_create_data,
        session,
        arbitrary_client,
        tom,
        applet_with_reviewable_activity,
        arbitrary_session,
    ):
        arbitrary_client.login(tom)
        answer_service = AnswerService(session, tom.id, arbitrary_session)
        answer = await answer_service.create_answer(tom_answer_create_data)
        await answer_service.create_assessment_answer(
            applet_with_reviewable_activity.id, answer.id, tom_answer_assessment_create_data
        )
        assessment = await AnswerItemsCRUD(arbitrary_session).get_assessment(answer.id, tom.id)
        assert assessment
        response = await arbitrary_client.delete(
            self.assessment_delete_url.format(
                applet_id=str(applet_with_reviewable_activity.id), answer_id=answer.id, assessment_id=assessment.id
            )
        )
        assert response.status_code == 204
        assessment = await AnswerItemsCRUD(arbitrary_session).get_assessment(answer.id, tom.id)
        assert not assessment

    async def test_applet_assessment_create_for_submission(
        self,
        arbitrary_client: TestClient,
        tom: User,
        arbitrary_session: AsyncSession,
        assessment_for_submission_arbitrary: AssessmentAnswerCreate,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
    ):
        assert assessment_submission_create.reviewed_flow_submit_id
        arbitrary_client.login(tom)
        applet_id = str(applet_with_reviewable_flow.id)
        flow_id = str(applet_with_reviewable_flow.activity_flows[0].id)
        submission_id = assessment_submission_create.reviewed_flow_submit_id
        response = await arbitrary_client.post(
            self.assessment_submissions_url.format(
                applet_id=applet_id, flow_id=flow_id, submission_id=str(submission_id)
            ),
            data=assessment_submission_create,
        )
        assert response.status_code == http.HTTPStatus.CREATED
        answer = await AnswersCRUD(arbitrary_session).get_last_answer_in_flow(submission_id)
        assert answer
        assessment = await AnswerItemsCRUD(arbitrary_session).get_assessment(answer.id, tom.id, submission_id)
        assert assessment
        assert assessment_submission_create.reviewed_flow_submit_id == assessment.reviewed_flow_submit_id

    async def test_applet_assessment_retrieve_for_submission(
        self,
        arbitrary_client: TestClient,
        tom: User,
        arbitrary_session: AsyncSession,
        assessment_for_submission_arbitrary: AssessmentAnswerCreate,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
        submission_assessment_answer: AnswerItemSchema,
    ):
        assert assessment_submission_create.reviewed_flow_submit_id
        arbitrary_client.login(tom)
        applet_id = str(applet_with_reviewable_flow.id)
        submission_id = str(assessment_submission_create.reviewed_flow_submit_id)
        response = await arbitrary_client.get(
            self.assessment_submissions_retrieve_url.format(
                applet_id=applet_id,
                submission_id=submission_id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()

    async def test_applet_assessment_delete_for_submission(
        self,
        arbitrary_client: TestClient,
        tom: User,
        session: AsyncSession,
        assessment_for_submission_arbitrary: AssessmentAnswerCreate,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
        submission_assessment_answer: AnswerItemSchema,
    ):
        assert assessment_submission_create.reviewed_flow_submit_id
        arbitrary_client.login(tom)
        applet_id = str(applet_with_reviewable_flow.id)
        submission_id = str(assessment_submission_create.reviewed_flow_submit_id)
        response = await arbitrary_client.delete(
            self.assessment_submission_delete_url.format(
                applet_id=applet_id, submission_id=submission_id, assessment_id=submission_assessment_answer.id
            )
        )
        assert response.status_code == http.HTTPStatus.NO_CONTENT
