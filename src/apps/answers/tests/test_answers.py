import datetime
import http
import re
import uuid
from collections import defaultdict
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from pytest import FixtureRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.crud import AnswerItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.db.schemas import AnswerItemSchema, AnswerNoteSchema, AnswerSchema
from apps.answers.domain import AnswerNote, AppletAnswerCreate, AssessmentAnswerCreate, ClientMeta, ItemAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain.applet_full import AppletFull
from apps.applets.errors import InvalidVersionError
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject, SubjectCreate
from apps.subjects.services import SubjectsService
from apps.users import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from infrastructure.utility import RedisCacheTest


@pytest.fixture(params=["none", "respondent", "subject"])
async def identifiers_query(request, tom_applet_subject: SubjectSchema):
    params_map = {
        "none": {},
        "respondent": {"respondentId": str(tom_applet_subject.user_id)},
        "subject": {"targetSubjectId": str(tom_applet_subject.id)},
    }
    return params_map[request.param]


def note_url_path_data(answer: AnswerSchema) -> dict[str, Any]:
    return {
        "applet_id": answer.applet_id,
        "answer_id": answer.id,
        "activity_id": answer.activity_history_id.split("_")[0],
    }


@pytest.fixture
async def bob_reviewer_in_applet_with_reviewable_activity(session, tom, bob, applet_with_reviewable_activity) -> User:
    tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(
        tom.id, applet_with_reviewable_activity.id
    )
    assert tom_subject, "Must have an subject for submitting answers"
    await UserAppletAccessCRUD(session).save(
        UserAppletAccessSchema(
            user_id=bob.id,
            applet_id=applet_with_reviewable_activity.id,
            role=Role.REVIEWER,
            owner_id=tom.id,
            invitor_id=tom.id,
            meta=dict(subjects=[str(tom_subject.id)]),
            nickname=str(uuid.uuid4()),
        )
    )
    return bob


@pytest.fixture
async def lucy_manager_in_applet_with_reviewable_activity(session, tom, lucy, applet_with_reviewable_activity) -> User:
    await UserAppletAccessCRUD(session).save(
        UserAppletAccessSchema(
            user_id=lucy.id,
            applet_id=applet_with_reviewable_activity.id,
            role=Role.MANAGER,
            owner_id=tom.id,
            invitor_id=tom.id,
            meta=dict(),
            nickname=str(uuid.uuid4()),
        )
    )
    return lucy


@pytest.fixture
def tom_answer_assessment_create_data(tom, applet_with_reviewable_activity) -> AssessmentAnswerCreate:
    activity_assessment_id = applet_with_reviewable_activity.activities[1].id
    return AssessmentAnswerCreate(
        answer="0x00",
        item_ids=[applet_with_reviewable_activity.activities[1].items[0].id],
        reviewer_public_key=f"{tom.id}",
        assessment_version_id=f"{activity_assessment_id}_{applet_with_reviewable_activity.version}",
    )


@pytest.fixture
async def tom_answer_item_for_applet(tom: User, applet: AppletFull, session: AsyncSession, tom_applet_subject):
    answer = await AnswersCRUD(session).create(
        AnswerSchema(
            applet_id=applet.id,
            version=applet.version,
            submit_id=uuid.uuid4(),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
            ),
            applet_history_id=f"{applet.id}_{applet.version}",
            activity_history_id=f"{applet.activities[0].id}_{applet.version}",
            respondent_id=tom.id,
            target_subject_id=tom_applet_subject.id,
            source_subject_id=tom_applet_subject.id,
        )
    )
    return dict(
        answer_id=answer.id,
        respondent_id=tom.id,
        answer=uuid.uuid4().hex,
        item_ids=[str(item.id) for item in applet.activities[0].items],
        start_datetime=datetime.datetime.utcnow(),
        end_datetime=datetime.datetime.utcnow(),
        is_assessment=False,
    )


@pytest.fixture
async def tom_answer(session: AsyncSession, tom: User, applet_with_reviewable_activity: AppletFull) -> AnswerSchema:
    answer_service = AnswerService(session, tom.id)
    return await answer_service.create_answer(
        AppletAnswerCreate(
            applet_id=applet_with_reviewable_activity.id,
            version=applet_with_reviewable_activity.version,
            submit_id=uuid.uuid4(),
            activity_id=applet_with_reviewable_activity.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_reviewable_activity.activities[0].items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
    )


@pytest.fixture
async def tom_answer_activity_flow(session: AsyncSession, tom: User, applet_with_flow: AppletFull) -> AnswerSchema:
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
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
                identifier="encrypted_identifier",
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
    )


@pytest.fixture
def applet_with_flow_answer_create(applet_with_flow: AppletFull) -> list[AppletAnswerCreate]:
    submit_id = uuid.uuid4()
    answer_data = dict(
        applet_id=applet_with_flow.id,
        version=applet_with_flow.version,
        client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
    )
    answer_item_data = dict(
        start_time=datetime.datetime.utcnow(),
        end_time=datetime.datetime.utcnow(),
        user_public_key=str(uuid.uuid4()),
    )
    answers = [
        # flow#1 submission#1
        AppletAnswerCreate(
            submit_id=uuid.uuid4(),
            flow_id=applet_with_flow.activity_flows[0].id,
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                identifier="encrypted_identifier",
                **answer_item_data,
            ),
            **answer_data,
        ),
        # flow#2 submission#1
        AppletAnswerCreate(
            submit_id=submit_id,
            flow_id=applet_with_flow.activity_flows[1].id,
            is_flow_completed=False,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                identifier="encrypted_identifierf2a1",
                **answer_item_data,
            ),
            **answer_data,
        ),
        AppletAnswerCreate(
            submit_id=submit_id,
            flow_id=applet_with_flow.activity_flows[1].id,
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[1].id,
            answer=ItemAnswerCreate(item_ids=[applet_with_flow.activities[1].items[0].id], **answer_item_data),
            **answer_data,
        ),
        # flow#1 submission#2
        AppletAnswerCreate(
            submit_id=uuid.uuid4(),
            flow_id=applet_with_flow.activity_flows[0].id,
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                identifier="encrypted_identifierf1a2",
                **answer_item_data,
            ),
            **answer_data,
        ),
    ]
    return answers


@pytest.fixture
async def tom_answer_activity_flow_multiple(
    session: AsyncSession, tom: User, applet_with_flow_answer_create
) -> list[AnswerSchema]:
    answer_service = AnswerService(session, tom.id)
    answers = []
    for _answer in applet_with_flow_answer_create:
        answer = await answer_service.create_answer(_answer)
        answers.append(answer)

    return answers


@pytest.fixture
async def tom_answer_activity_no_flow(session: AsyncSession, tom: User, applet_with_flow: AppletFull) -> AnswerSchema:
    answer_service = AnswerService(session, tom.id)
    return await answer_service.create_answer(
        AppletAnswerCreate(
            applet_id=applet_with_flow.id,
            version=applet_with_flow.version,
            submit_id=uuid.uuid4(),
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
    )


@pytest.fixture
async def tom_review_answer(
    session: AsyncSession, tom: User, applet_with_reviewable_activity: AppletFull, tom_answer: AnswerSchema
):
    applet_id = applet_with_reviewable_activity.id
    activity_assessment_id = applet_with_reviewable_activity.activities[1].id
    assessment = AssessmentAnswerCreate(
        answer=uuid.uuid4().hex,
        item_ids=[applet_with_reviewable_activity.activities[1].items[0].id],
        reviewer_public_key=f"{tom.id}",
        assessment_version_id=f"{activity_assessment_id}_{applet_with_reviewable_activity.version}",
    )
    await AnswerService(session, tom.id).create_assessment_answer(applet_id, tom_answer.id, assessment)


@pytest.fixture
async def bob_review_answer(
    session: AsyncSession, bob: User, applet_with_reviewable_activity: AppletFull, tom_answer: AnswerSchema
):
    applet_id = applet_with_reviewable_activity.id
    activity_assessment_id = applet_with_reviewable_activity.activities[1].id
    assessment = AssessmentAnswerCreate(
        answer=uuid.uuid4().hex,
        item_ids=[applet_with_reviewable_activity.activities[1].items[0].id],
        reviewer_public_key=f"{bob.id}",
        assessment_version_id=f"{activity_assessment_id}_{applet_with_reviewable_activity.version}",
    )
    await AnswerService(session, bob.id).create_assessment_answer(applet_id, tom_answer.id, assessment)


@pytest.fixture
async def lucy_review_answer(
    session: AsyncSession, lucy: User, applet_with_reviewable_activity: AppletFull, tom_answer: AnswerSchema
):
    applet_id = applet_with_reviewable_activity.id
    activity_assessment_id = applet_with_reviewable_activity.activities[1].id
    assessment = AssessmentAnswerCreate(
        answer=uuid.uuid4().hex,
        item_ids=[applet_with_reviewable_activity.activities[1].items[0].id],
        reviewer_public_key=f"{lucy.id}",
        assessment_version_id=f"{activity_assessment_id}_{applet_with_reviewable_activity.version}",
    )
    await AnswerService(session, lucy.id).create_assessment_answer(applet_id, tom_answer.id, assessment)


@pytest.mark.usefixtures("mock_kiq_report")
class TestAnswerActivityItems(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]

    login_url = "/auth/login"
    answer_url = "/answers"
    public_answer_url = "/public/answers"

    review_activities_url = "/answers/applet/{applet_id}/review/activities"
    review_flows_url = "/answers/applet/{applet_id}/review/flows"

    summary_activities_url = "/answers/applet/{applet_id}/summary/activities"
    summary_activity_flows_url = "/answers/applet/{applet_id}/summary/flows"
    activity_identifiers_url = f"{summary_activities_url}/{{activity_id}}/identifiers"
    flow_identifiers_url = "/answers/applet/{applet_id}/flows/{flow_id}/identifiers"
    activity_versions_url = f"{summary_activities_url}/{{activity_id}}/versions"
    flow_versions_url = "/answers/applet/{applet_id}/flows/{flow_id}/versions"

    activity_answers_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers"
    flow_submissions_url = "/answers/applet/{applet_id}/flows/{flow_id}/submissions"
    applet_answers_export_url = "/answers/applet/{applet_id}/data"
    applet_answers_completions_url = "/answers/applet/{applet_id}/completions"
    applets_answers_completions_url = "/answers/applet/completions"
    applet_submit_dates_url = "/answers/applet/{applet_id}/dates"

    activity_answer_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{answer_id}"
    flow_submission_url = "/answers/applet/{applet_id}/flows/{flow_id}/submissions/{submit_id}"
    assessment_answers_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment"

    answer_reviews_url = "/answers/applet/{applet_id}/answers/{answer_id}/reviews"
    answer_notes_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes"
    answer_note_detail_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes/{note_id}"
    latest_report_url = "/answers/applet/{applet_id}/activities/{activity_id}/subjects/{subject_id}/latest_report"
    check_existence_url = "/answers/check-existence"
    assessment_delete_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment/{assessment_id}"

    async def test_answer_activity_items_create_for_respondent(
        self,
        mock_kiq_report: AsyncMock,
        client: TestClient,
        tom: User,
        redis: RedisCacheTest,
        answer_with_alert_create: AppletAnswerCreate,
        mailbox: TestMail,
        session: AsyncSession,
    ) -> None:
        client.login(tom)
        # TODO: Solve sqlalchemy.exc.MissingGreenlet and use fixture 'tom_applet_subject' instead
        subject = await SubjectsService(session, tom.id).get_by_user_and_applet(
            tom.id, answer_with_alert_create.applet_id
        )
        assert subject
        response = await client.post(self.answer_url, data=answer_with_alert_create)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        mock_kiq_report.assert_awaited_once()

        published_values = await redis.get(f"channel_{tom.id}")
        published_values = published_values or []
        assert len(published_values) == 1
        # 2 because alert for lucy and for tom
        assert len(redis._storage) == 1
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].subject == "Response alert"

        response = await client.get(
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
        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(answer_with_alert_create.applet_id),
                answer_id=answer_id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()

    async def test_create_answer__wrong_applet_version(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        client.login(tom)
        data = answer_create.copy(deep=True)
        data.version = "0.0.0"
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == InvalidVersionError.message

    @pytest.mark.usefixtures("mock_report_server_response", "answer")
    async def test_get_latest_summary(
        self, client: TestClient, tom: User, applet: AppletFull, tom_applet_subject: Subject
    ):
        client.login(tom)

        response = await client.post(
            self.latest_report_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
                subject_id=str(tom_applet_subject.id),
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.content == b"pdf body"

    async def test_public_answer_activity_items_create_for_respondent(
        self, client: TestClient, public_answer_create: AppletAnswerCreate
    ):
        response = await client.post(self.public_answer_url, data=public_answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

    async def test_answer_skippable_activity_items_create_for_respondent(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate, applet: AppletFull
    ):
        client.login(tom)

        response = await client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]["dates"]) == 1

    async def test_list_submit_dates(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate, applet: AppletFull
    ):
        client.login(tom)

        response = await client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]["dates"]) == 1

    async def test_answer_flow_items_create_for_respondent(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate
    ):
        client.login(tom)

        response = await client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED

    async def test_answer_get_export_data__answer_from_manager(
        self,
        client: TestClient,
        tom: User,
        lucy: User,
        answer_create: AppletAnswerCreate,
        applet_one_lucy_manager: AppletFull,
        applet_one_lucy_respondent: AppletFull,
    ):
        client.login(lucy)
        data = answer_create.copy(deep=True)
        data.applet_id = applet_one_lucy_manager.id
        data.version = applet_one_lucy_manager.version
        data.activity_id = applet_one_lucy_manager.activities[0].id
        data.flow_id = None
        data.answer.item_ids = [i.id for i in applet_one_lucy_manager.activities[0].items]
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        client.login(tom)
        response = await client.get(
            self.applet_answers_export_url.format(applet_id=str(applet_one_lucy_manager.id)),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert re.match(
            r"\[admin account\] \([0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12}\)",
            response.json()["result"]["answers"][0]["respondentSecretId"],
        )

    async def test_answer_get_export_data__answer_from_respondent(
        self,
        client: TestClient,
        tom: User,
        lucy: User,
        answer_create: AppletAnswerCreate,
        applet_one_lucy_respondent: AppletFull,
    ):
        client.login(lucy)
        data = answer_create.copy(deep=True)
        data.applet_id = applet_one_lucy_respondent.id
        data.version = applet_one_lucy_respondent.version
        data.activity_id = applet_one_lucy_respondent.activities[0].id
        data.flow_id = None
        data.answer.item_ids = [i.id for i in applet_one_lucy_respondent.activities[0].items]
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        client.login(tom)
        response = await client.get(
            self.applet_answers_export_url.format(applet_id=str(applet_one_lucy_respondent.id)),
        )
        assert response.status_code == http.HTTPStatus.OK
        secret_user_id = response.json()["result"]["answers"][0]["respondentSecretId"]
        assert secret_user_id != f"[admin account] ({lucy.email_encrypted})"
        assert uuid.UUID(secret_user_id)

    async def test_answer_get_export_data__only_last_activity(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet: AppletFull,
        applet_with_additional_item: AppletFull,  # next version of applet
    ):
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.get(
            self.applet_answers_export_url.format(applet_id=str(applet.id)), query={"activitiesLastVersion": True}
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["activities"][0]["id"] == str(applet_with_additional_item.activities[0].id)
        assert response.json()["result"]["activities"][0]["version"] == applet_with_additional_item.version
        assert (
            response.json()["result"]["activities"][0]["idVersion"]
            == f"{applet_with_additional_item.activities[0].id}_{applet_with_additional_item.version}"
        )

    async def test_answer_with_skipping_all(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

    async def test_answered_applet_activities_1(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate, session: AsyncSession
    ):
        client.login(tom)

        response = await client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        # TODO: Fix sqlalchemy.exc.MissingGreenlet and use fixture instead
        subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, answer_create.applet_id)
        assert subject
        response = await client.get(
            self.review_activities_url.format(applet_id=str(answer_create.applet_id)),
            dict(
                targetSubjectId=subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.activity_answer_url.format(
                applet_id=str(answer_create.applet_id),
                answer_id=answer_id,
                activity_id=str(answer_create.activity_id),
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]
        assert data["answer"]["events"] == answer_create.answer.events
        assert set(data["summary"]["identifier"]) == {"lastAnswerDate", "identifier", "userPublicKey"}
        assert data["summary"]["identifier"]["identifier"] == "encrypted_identifier"

    async def test_get_answer_activity(self, client: TestClient, tom: User, applet: AppletFull, answer: AnswerSchema):
        client.login(tom)
        response = await client.get(
            self.activity_answer_url.format(
                applet_id=str(applet.id),
                answer_id=answer.id,
                activity_id=applet.activities[0].id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK  # TODO: Check response

    async def test_fail_answered_applet_not_existed_activities(
        self, client: TestClient, tom: User, applet: AppletFull, uuid_zero: uuid.UUID, answer: AnswerSchema
    ):
        client.login(tom)
        response = await client.get(
            self.activity_answer_url.format(
                applet_id=str(applet.id),
                answer_id=answer.id,
                activity_id=uuid_zero,
            )
        )
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_applet_activity_answers(
        self, client: TestClient, tom: User, applet: AppletFull, answer: AnswerSchema
    ):
        client.login(tom)
        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1

    async def test_applet_assessment_retrieve(
        self, client: TestClient, tom: User, answer_reviewable_activity: AnswerSchema
    ):
        client.login(tom)
        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(answer_reviewable_activity.applet_id),
                answer_id=answer_reviewable_activity.id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]

    async def test_applet_assessment_create(
        self,
        client: TestClient,
        tom: User,
        assessment_create: AssessmentAnswerCreate,
        answer_reviewable_activity: AnswerSchema,
        applet_with_reviewable_activity: AppletFull,
    ):
        client.login(tom)

        response = await client.post(
            self.assessment_answers_url.format(
                applet_id=str(answer_reviewable_activity.applet_id),
                answer_id=answer_reviewable_activity.id,
            ),
            data=assessment_create,
        )

        assert response.status_code == http.HTTPStatus.CREATED
        review_activity = next(i for i in applet_with_reviewable_activity.activities if i.is_reviewable)
        general_activity = next(i for i in applet_with_reviewable_activity.activities if not i.is_reviewable)

        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(answer_reviewable_activity.applet_id),
                answer_id=answer_reviewable_activity.id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        assessment = response.json()["result"]
        assert assessment["answer"] == assessment_create.answer
        assert assessment["reviewerPublicKey"] == assessment_create.reviewer_public_key
        assert assessment["itemIds"] == [str(i) for i in assessment_create.item_ids]
        assert assessment["versions"] == [
            f"{general_activity.id}_{applet_with_reviewable_activity.version}",
            f"{review_activity.id}_{applet_with_reviewable_activity.version}",
        ]
        assert not assessment["itemsLast"] == general_activity.dict()["items"][0]
        assert not assessment["items"]

    @pytest.mark.usefixtures("assessment")
    async def test_get_review_assessment(
        self,
        client: TestClient,
        tom: User,
        answer_reviewable_activity: AnswerSchema,
        assessment_create: AssessmentAnswerCreate,
    ):
        client.login(tom)
        response = await client.get(
            self.answer_reviews_url.format(
                applet_id=str(answer_reviewable_activity.applet_id),
                answer_id=answer_reviewable_activity.id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        assert set(response.json()["result"][0].keys()) == {
            "answer",
            "createdAt",
            "updatedAt",
            "id",
            "itemIds",
            "items",
            "reviewer",
            "reviewerPublicKey",
        }
        assert response.json()["count"] == 1
        review = response.json()["result"][0]
        assert review["answer"] == assessment_create.answer
        assert review["reviewerPublicKey"] == assessment_create.reviewer_public_key
        assert review["itemIds"] == [str(i) for i in assessment_create.item_ids]
        assert review["reviewer"]["firstName"] == tom.first_name
        assert review["reviewer"]["lastName"] == tom.last_name

    async def test_applet_activities(self, client: TestClient, tom: User, answer: AnswerSchema, tom_applet_subject):
        client.login(tom)

        response = await client.get(
            self.review_activities_url.format(applet_id=str(answer.applet_id)),
            dict(
                targetSubjectId=tom_applet_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

    async def test_add_note(self, client: TestClient, tom: User, answer: AnswerSchema, note_create_data: AnswerNote):
        client.login(tom)

        response = await client.post(self.answer_notes_url.format(**note_url_path_data(answer)), data=note_create_data)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(self.answer_notes_url.format(**note_url_path_data(answer)))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        note = response.json()["result"][0]
        assert note["note"] == note_create_data.note
        assert note["user"]["firstName"] == tom.first_name
        assert note["user"]["lastName"] == tom.last_name
        # Just check that other columns in place
        assert note["id"]
        assert note["createdAt"]

    async def test_edit_note(self, client: TestClient, tom: User, answer: AnswerSchema, answer_note: AnswerNoteSchema):
        client.login(tom)

        note_new = answer_note.note + "new"

        response = await client.put(
            self.answer_note_detail_url.format(**note_url_path_data(answer), note_id=answer_note.id),
            dict(note=note_new),
        )
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(self.answer_notes_url.format(**note_url_path_data(answer)))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == note_new

    async def test_delete_note(
        self, client: TestClient, tom: User, answer: AnswerSchema, answer_note: AnswerNoteSchema
    ):
        client.login(tom)
        note_id = answer_note.id

        response = await client.delete(
            self.answer_note_detail_url.format(**note_url_path_data(answer), note_id=note_id)
        )
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        response = await client.get(self.answer_notes_url.format(**note_url_path_data(answer)))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 0

    async def test_answer_activity_items_create_for_not_respondent(
        self, client: TestClient, user: User, answer_create: AppletAnswerCreate
    ):
        client.login(user)
        response = await client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    @pytest.mark.usefixtures("assessment")
    async def test_answers_export(
        self,
        client: TestClient,
        tom: User,
        answer_reviewable_activity_with_ts_offset: AnswerSchema,
        answer_reviewable_activity_with_tz_offset_create: AppletAnswerCreate,
    ):
        client.login(tom)
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id=str(answer_reviewable_activity_with_ts_offset.applet_id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        resp_data = response.json()
        data = resp_data["result"]
        assert set(data.keys()) == {"answers", "activities"}
        # One answer, one answer with ts offset, one assessment
        assert len(data["answers"]) == 3
        assert resp_data["count"] == 3
        assessment = next(i for i in data["answers"] if i["reviewedAnswerId"] is not None)
        answer_with_tz = next(i for i in data["answers"] if i["tzOffset"] is not None)
        answer_for_review = next(i for i in data["answers"] if i["id"] == assessment["reviewedAnswerId"])
        # fmt: off
        expected_keys = {
            "activityHistoryId", "activityId", "answer", "appletHistoryId",
            "appletId", "createdAt", "events", "flowHistoryId", "flowId",
            "flowName", "id", "itemIds", "migratedData", "respondentId",
            "respondentSecretId", "reviewedAnswerId", "userPublicKey",
            "version", "submitId", "scheduledDatetime", "startDatetime",
            "endDatetime", "legacyProfileId", "migratedDate",
            "relation", "sourceSubjectId", "targetSubjectId", "client",
            "tzOffset", "scheduledEventId",
        }
        # Comment for now, wtf is it
        # assert int(answer['startDatetime'] * 1000) == answer_item_create.start_time
        # fmt: on
        answer_reviewable_activity_with_tz_offset_create.answer.tz_offset = cast(
            int, answer_reviewable_activity_with_tz_offset_create.answer.tz_offset
        )
        assert answer_with_tz["tzOffset"] == answer_reviewable_activity_with_tz_offset_create.answer.tz_offset
        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer_for_review["id"]
        assert re.match(
            r"\[admin account\] \([0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12}\)",
            answer_for_review["respondentSecretId"],
        )

    @pytest.mark.parametrize(
        "user_fixture, exp_cnt",
        (
            ("lucy", 0),
            ("tom", 1),  # Tom is respondent for the 'answer' fixture
        ),
    )
    async def test_get_applet_answers_export_filter_by_respondent_id(
        self,
        client: TestClient,
        tom: User,
        answer: AnswerSchema,
        request: FixtureRequest,
        user_fixture: str,
        exp_cnt: int,
    ):
        client.login(tom)
        respondent: User = request.getfixturevalue(user_fixture)
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id=str(answer.applet_id),
            ),
            dict(respondentIds=str(respondent.id)),
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == exp_cnt
        assert len(response.json()["result"]["answers"]) == exp_cnt

    async def test_get_activity_identifiers(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate, applet: AppletFull
    ):
        client.login(tom)
        identifier_url = self.activity_identifiers_url.format(
            applet_id=str(applet.id), activity_id=str(applet.activities[0].id)
        )
        identifier_url = f"{identifier_url}?respondentId={tom.id}"
        response = await client.get(identifier_url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 0

        created_at = datetime.datetime.utcnow()
        data = answer_create.copy(deep=True)
        data.created_at = created_at

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.get(identifier_url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["identifier"] == answer_create.answer.identifier
        assert response.json()["result"][0]["userPublicKey"] == answer_create.answer.user_public_key
        assert datetime.datetime.fromisoformat(response.json()["result"][0]["lastAnswerDate"]) == created_at

    async def test_get_flow_identifiers(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        applet_with_flow_answer_create: list[AppletAnswerCreate],
        tom_answer_activity_flow_multiple,
        session,
    ):
        applet = applet_with_flow
        answers = applet_with_flow_answer_create
        client.login(tom)

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet.id)
        assert tom_subject
        for flow in applet.activity_flows:
            flow_answers = [
                answer for answer in answers if answer.flow_id == flow.id and answer.answer.identifier is not None
            ]

            identifier_url = self.flow_identifiers_url.format(applet_id=applet.id, flow_id=flow.id)
            response = await client.get(identifier_url, dict(targetSubjectId=tom_subject.id))

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == len(flow_answers)
            data = data["result"]
            for i, _answer in enumerate(flow_answers):
                assert set(data[i].keys()) == {"identifier", "userPublicKey", "lastAnswerDate"}
                assert data[i]["identifier"] == _answer.answer.identifier
                assert data[i]["userPublicKey"] == _answer.answer.user_public_key

    # TODO: Move to another place, not needed any answer for test
    async def test_get_all_activity_versions_for_applet(self, client: TestClient, tom: User, applet: AppletFull):
        client.login(tom)

        response = await client.get(
            self.activity_versions_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["version"] == applet.version
        assert response.json()["result"][0]["createdAt"]

    async def test_get_summary_activities_no_answer_no_performance_task(
        self, client: TestClient, tom: User, applet: AppletFull
    ):
        client.login(tom)

        response = await client.get(
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

    async def test_get_flow_versions(self, client, tom, applet_with_flow: AppletFull):
        client.login(tom)

        response = await client.get(
            self.flow_versions_url.format(
                applet_id=applet_with_flow.id,
                flow_id=applet_with_flow.activity_flows[0].id,
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        data = response.json()["result"]
        assert set(data[0].keys()) == {"version", "createdAt"}
        assert response.json()["result"][0]["version"] == applet_with_flow.version

    @pytest.mark.usefixtures("answer")
    async def test_get_summary_activities_has_answer_no_performance_task(
        self, client: TestClient, tom: User, applet: AppletFull, tom_applet_subject
    ):
        client.login(tom)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            ),
            query={"targetSubjectId": tom_applet_subject.id},
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        activity = response.json()["result"][0]
        assert activity["name"] == applet.activities[0].name
        assert activity["id"] == str(applet.activities[0].id)
        assert not activity["isPerformanceTask"]
        assert activity["hasAnswer"]

    async def test_get_summary_activities_performance_tasks_no_answers(
        self, client: TestClient, tom: User, applet_with_all_performance_tasks: AppletFull
    ):
        client.login(tom)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_with_all_performance_tasks.id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == len(applet_with_all_performance_tasks.activities)
        applet_with_all_performance_tasks.activities.sort(key=lambda x: x.id)
        sorted_result = sorted(response.json()["result"], key=lambda x: x["id"])
        for exp, act in zip(applet_with_all_performance_tasks.activities, sorted_result):
            assert act["id"] == str(exp.id)
            assert act["name"] == exp.name
            assert act["isPerformanceTask"]
            assert not act["hasAnswer"]

    async def test_store_client_meta(
        self, client: TestClient, session: AsyncSession, tom: User, answer_create: AppletAnswerCreate
    ):
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

        db_result = await session.execute(select(AnswerSchema))
        res: AnswerSchema = db_result.scalars().first()
        assert res.client["app_id"] == answer_create.client.app_id
        assert res.client["app_version"] == answer_create.client.app_version
        assert res.client["width"] == answer_create.client.width
        assert res.client["height"] == answer_create.client.height

    async def test_activity_answers_by_identifier(
        self, client: TestClient, tom: User, answer: AnswerSchema, answer_create: AppletAnswerCreate
    ):
        client.login(tom)

        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(answer_create.applet_id),
                activity_id=str(answer_create.activity_id),
            ),
            query={"emptyIdentifiers": False, "identifiers": answer_create.answer.identifier},
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()
        assert result["count"] == 1
        assert result["result"][0]["answerId"] == str(answer.id)

    async def test_applet_completions(
        self, client: TestClient, tom: User, answer: AnswerSchema, answer_create: AppletAnswerCreate
    ):
        client.login(tom)
        answer_create.answer.local_end_date = cast(datetime.date, answer_create.answer.local_end_date)
        answer_create.answer.local_end_time = cast(datetime.time, answer_create.answer.local_end_time)
        response = await client.get(
            self.applet_answers_completions_url.format(
                applet_id=str(answer.applet_id),
            ),
            {"fromDate": answer_create.answer.local_end_date.isoformat(), "version": answer.version},
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
            "scheduledEventId",
            "localEndDate",
            "localEndTime",
        }
        assert activity_answer_data["answerId"] == str(answer.id)
        assert activity_answer_data["localEndTime"] == str(answer_create.answer.local_end_time)

    async def test_applets_completions(
        self, client: TestClient, tom: User, answer: AnswerSchema, answer_create: AppletAnswerCreate
    ):
        client.login(tom)
        answer_create.answer.local_end_date = cast(datetime.date, answer_create.answer.local_end_date)
        answer_create.answer.local_end_time = cast(datetime.time, answer_create.answer.local_end_time)
        # test completions
        response = await client.get(
            url=self.applets_answers_completions_url,
            query={"fromDate": answer_create.answer.local_end_date.isoformat()},
        )

        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]
        # 2 session applets and 1 for answers
        assert len(data) == 3
        applet_with_answer = next(i for i in data if i["id"] == str(answer.applet_id))

        assert applet_with_answer["id"] == str(answer.applet_id)
        assert applet_with_answer["version"] == answer.version
        assert len(applet_with_answer["activities"]) == 1
        activity_answer_data = applet_with_answer["activities"][0]
        assert set(activity_answer_data.keys()) == {
            "id",
            "answerId",
            "submitId",
            "scheduledEventId",
            "localEndDate",
            "localEndTime",
        }
        assert activity_answer_data["answerId"] == str(answer.id)
        assert activity_answer_data["scheduledEventId"] == answer_create.answer.scheduled_event_id
        assert activity_answer_data["localEndDate"] == answer_create.answer.local_end_date.isoformat()
        assert activity_answer_data["localEndTime"] == str(answer_create.answer.local_end_time)
        for applet_data in data:
            if applet_data["id"] != str(answer.applet_id):
                assert not applet_data["activities"]
                assert not applet_data["activityFlows"]

    async def test_summary_restricted_for_reviewer_if_external_respondent(
        self, client: TestClient, user: User, user_reviewer_applet_one: AppletFull
    ):
        client.login(user)

        response = await client.get(self.summary_activities_url.format(applet_id=str(user_reviewer_applet_one.id)))

        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_public_answer_with_zero_start_time_end_time_timestamps(
        self, client: TestClient, public_answer_create: AppletAnswerCreate
    ):
        create_data = public_answer_create.dict()
        create_data["answer"]["start_time"] = 0
        create_data["answer"]["end_time"] = 0

        response = await client.post(self.public_answer_url, data=create_data)

        assert response.status_code == http.HTTPStatus.CREATED

    async def test_check_existance_answer_exists(self, client: TestClient, tom: User, answer: AnswerSchema):
        client.login(tom)
        data = {
            "applet_id": str(answer.applet_id),
            "activity_id": answer.activity_history_id.split("_")[0],
            # On backend we devide on 1000
            "created_at": answer.created_at.timestamp() * 1000,
        }
        resp = await client.post(self.check_existence_url, data=data)
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
        self, client: TestClient, tom: User, answer: AnswerSchema, column: str, value: str
    ):
        client.login(tom)
        data = {
            "applet_id": str(answer.applet_id),
            "activity_id": answer.activity_history_id.split("_")[0],
            "created_at": answer.created_at.timestamp(),
        }
        data[column] = value
        resp = await client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]["exists"]

    async def test_check_existance_answer_does_not_exist__not_answer_applet(
        self, client: TestClient, tom: User, answer: AnswerSchema, applet_one: AppletFull
    ):
        client.login(tom)
        data = {
            "applet_id": str(applet_one.id),
            "activity_id": answer.activity_history_id.split("_")[0],
            "created_at": answer.created_at.timestamp(),
        }
        resp = await client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]["exists"]

    @pytest.mark.parametrize(
        "user_fixture_name,expected_code",
        (
            ("tom", http.HTTPStatus.NO_CONTENT),  # owner
            ("lucy", http.HTTPStatus.FORBIDDEN),  # not in applet
            ("bob", http.HTTPStatus.FORBIDDEN),  # reviewer
        ),
    )
    async def test_review_delete(
        self,
        tom_answer_create_data,
        tom_answer_assessment_create_data,
        client,
        tom,
        applet_with_reviewable_activity,
        session,
        bob_reviewer_in_applet_with_reviewable_activity,
        user_fixture_name,
        expected_code,
        request,
        tom_answer,
        tom_review_answer,
    ):
        login_user = request.getfixturevalue(user_fixture_name)
        client.login(login_user)
        assessment = await AnswerItemsCRUD(session).get_assessment(tom_answer.id, tom.id)
        assert assessment
        response = await client.delete(
            self.assessment_delete_url.format(
                applet_id=str(applet_with_reviewable_activity.id), answer_id=tom_answer.id, assessment_id=assessment.id
            )
        )
        assert response.status_code == expected_code
        assessment = await AnswerItemsCRUD(session).get_assessment(tom_answer.id, tom.id)
        if expected_code == 204:
            assert not assessment
        else:
            assert assessment

    async def test_summary_activities_submitted_without_answers(
        self,
        client,
        tom,
        applet_with_reviewable_activity,
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_id),
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        payload = response.json()
        actual_last_date = payload["result"][0]["lastAnswerDate"]
        assert actual_last_date is None

    async def test_get_all_types_of_activity_identifiers(
        self, client, tom: User, applet: AppletFull, session, tom_answer_item_for_applet, tom_applet_subject
    ):
        client.login(tom)
        identifier_url = self.activity_identifiers_url.format(
            applet_id=str(applet.id), activity_id=str(applet.activities[0].id)
        )
        identifier_url = f"{identifier_url}?targetSubjectId={tom_applet_subject.id}"

        answer_items = [
            # Migrated not encrypted
            AnswerItemSchema(
                **tom_answer_item_for_applet,
                identifier="unencrypted identifier",
                migrated_data=dict(is_identifier_encrypted=False),
            ),
            # Migrated encrypted
            AnswerItemSchema(
                **tom_answer_item_for_applet,
                identifier="encrypted identifier",
                user_public_key="user_public_key",
                migrated_data=dict(is_identifier_encrypted=True),
            ),
            # Not migrated
            AnswerItemSchema(
                **tom_answer_item_for_applet,
                identifier="identifier",
                user_public_key="user_public_key",
                migrated_data=None,
            ),
        ]
        for answer_item in answer_items:
            await AnswerItemsCRUD(session).create(answer_item)

        res = await client.get(identifier_url)
        assert res.status_code == http.HTTPStatus.OK
        payload = res.json()
        assert payload["count"] == len(answer_items)
        for identifier in payload["result"]:
            assert "lastAnswerDate" in identifier
            if identifier["identifier"] in ["encrypted identifier", "identifier"]:
                assert "userPublicKey" in identifier

    async def test_summary_activities_submitted_date_with_answers(
        self,
        client,
        tom,
        applet_with_reviewable_activity,
        session,
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        answer_service = AnswerService(session, tom.id)
        submit_dates = []
        for i in range(2):
            answer = await answer_service.create_answer(
                AppletAnswerCreate(
                    applet_id=applet_with_reviewable_activity.id,
                    version=applet_with_reviewable_activity.version,
                    submit_id=uuid.uuid4(),
                    activity_id=applet_with_reviewable_activity.activities[0].id,
                    answer=ItemAnswerCreate(
                        item_ids=[applet_with_reviewable_activity.activities[0].items[0].id],
                        start_time=datetime.datetime.utcnow(),
                        end_time=datetime.datetime.utcnow(),
                        user_public_key=str(tom.id),
                    ),
                    client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
                )
            )
            submit_dates.append(answer.created_at)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_id),
            )
        )
        assert response.status_code == 200
        payload = response.json()
        expected_last_date = str(max(submit_dates))
        actual_last_date = payload["result"][0]["lastAnswerDate"].replace("T", " ")
        assert actual_last_date == expected_last_date

    async def test_answer_reviewer_count_for_multiple_reviews(
        self,
        client,
        tom,
        applet_with_reviewable_activity,
        tom_answer,
        tom_review_answer,
        bob_review_answer,
        lucy_review_answer,
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        activity_id = applet_with_reviewable_activity.activities[0].id
        url = self.activity_answers_url.format(applet_id=str(applet_id), activity_id=str(activity_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload["result"][0]["reviewCount"]["mine"] == 1
        assert payload["result"][0]["reviewCount"]["other"] == 2

    async def test_answer_reviewer_count_for_one_own_review(
        self, client, tom, applet_with_reviewable_activity: AppletFull, tom_answer, tom_review_answer
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        activity_id = applet_with_reviewable_activity.activities[0].id
        url = self.activity_answers_url.format(applet_id=str(applet_id), activity_id=str(activity_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload["result"][0]["reviewCount"]["mine"] == 1
        assert payload["result"][0]["reviewCount"]["other"] == 0

    async def test_answer_reviewer_count_for_one_other_review(
        self, client, tom, applet_with_reviewable_activity: AppletFull, tom_answer, bob_review_answer
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        activity_id = applet_with_reviewable_activity.activities[0].id
        url = self.activity_answers_url.format(applet_id=str(applet_id), activity_id=str(activity_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload["result"][0]["reviewCount"]["mine"] == 0
        assert payload["result"][0]["reviewCount"]["other"] == 1

    @pytest.mark.parametrize(
        "user_fixture,role",
        (
            ("tom", Role.OWNER),
            ("lucy", Role.MANAGER),
            ("bob", Role.REVIEWER),
        ),
    )
    async def test_owner_can_view_all_reviews_other_can_see_empty_encrypted_data(
        self,
        bob_reviewer_in_applet_with_reviewable_activity,
        lucy_manager_in_applet_with_reviewable_activity,
        tom_answer,
        tom_review_answer,
        bob_review_answer,
        client,
        tom,
        applet_with_reviewable_activity,
        session,
        request,
        user_fixture,
        role,
    ):
        login_user = request.getfixturevalue(user_fixture)
        client.login(login_user)
        result = await client.get(
            self.answer_reviews_url.format(applet_id=applet_with_reviewable_activity.id, answer_id=tom_answer.id)
        )
        assert result.status_code == 200
        payload = result.json()
        assert payload
        assert payload["count"] == 2

        results = payload["result"]
        for review in results:
            reviewer_id = uuid.UUID(review["reviewer"]["id"])
            if role == Role.REVIEWER and login_user.id != reviewer_id:
                assert review["answer"] is None
                assert review["reviewerPublicKey"] is None
            else:
                assert review["answer"] is not None
                assert review["reviewerPublicKey"] is not None

    async def test_get_summary_activities_after_upgrading_version(
        self,
        client,
        tom,
        applet_with_reviewable_activity,
        tom_answer,
        session,
    ):
        client.login(tom)
        answer_crud = AnswersCRUD(session)
        answer = await answer_crud.get_by_id(tom_answer.id)

        # Downgrade version on answer
        activity_id = answer.activity_history_id.split("_")[0]
        answer.activity_history_id = f"{activity_id}_1.0.0"
        answer.version = "1.0.0"
        await answer_crud._update_one("id", answer.id, answer)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
            )
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["hasAnswer"] is True

    async def test_review_flows_one_answer(
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow, session
    ):
        client.login(tom)
        url = self.review_flows_url.format(applet_id=applet_with_flow.id)

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject

        response = await client.get(
            url,
            dict(
                targetSubjectId=tom_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert len(data) == len(applet_with_flow.activity_flows)
        assert set(data[0].keys()) == {"id", "name", "answerDates", "lastAnswerDate"}
        for i, row in enumerate(data):
            assert row["id"] == str(applet_with_flow.activity_flows[i].id)
            assert row["name"] == applet_with_flow.activity_flows[i].name
        assert len(data[0]["answerDates"]) == 1
        assert set(data[0]["answerDates"][0].keys()) == {"submitId", "createdAt", "endDatetime"}
        assert len(data[1]["answerDates"]) == 0

    async def test_review_flows_multiple_answers(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow_multiple,
        session,
    ):
        client.login(tom)
        url = self.review_flows_url.format(applet_id=applet_with_flow.id)
        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject
        response = await client.get(
            url,
            dict(
                targetSubjectId=tom_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert len(data) == len(applet_with_flow.activity_flows)
        assert len(data[0]["answerDates"]) == 2
        assert len(data[1]["answerDates"]) == 1

    async def test_flow_submission(self, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow):
        client.login(tom)
        url = self.flow_submission_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
            submit_id=tom_answer_activity_flow.submit_id,
        )
        response = await client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert set(data.keys()) == {"flow", "submission", "summary"}

        assert len(data["submission"]["answers"]) == len(applet_with_flow.activity_flows[0].items)
        answer_data = data["submission"]["answers"][0]
        # fmt: off
        assert set(answer_data.keys()) == {
            "activityHistoryId", "activityId", "answer", "createdAt", "endDatetime", "events", "flowHistoryId", "id",
            "identifier", "itemIds", "migratedData", "submitId", "userPublicKey", "version"
        }
        assert answer_data["submitId"] == str(tom_answer_activity_flow.submit_id)
        assert answer_data["flowHistoryId"] == str(tom_answer_activity_flow.flow_history_id)

        assert set(data["flow"].keys()) == {
            "id", "activities", "createdAt", "description", "hideBadge", "idVersion", "isHidden", "isSingleReport",
            "name", "order", "reportIncludedActivityName","reportIncludedItemName"
        }
        assert len(data["flow"]["activities"]) == len(applet_with_flow.activity_flows[0].items)
        assert set(data["flow"]["activities"][0].keys()) == {
            "createdAt", "isSkippable", "showAllAtOnce", "subscaleSetting", "order", "name", "isHidden",
            "scoresAndReports", "isReviewable", "idVersion", "items", "performanceTaskType", "responseIsEditable",
            "appletId", "reportIncludedItemName", "description", "id", "splashScreen", "image"
        }
        assert len(data["flow"]["activities"][0]["items"]) == len(applet_with_flow.activities[0].items)
        assert set(data["flow"]["activities"][0]["items"][0].keys()) == {
            "activityId", "allowEdit", "conditionalLogic", "config", "id", "idVersion", "isHidden", "name", "order",
            "question", "responseType", "responseValues"
        }
        assert data["flow"]["idVersion"] == tom_answer_activity_flow.flow_history_id

        assert set(data["summary"].keys()) == {"identifier", "endDatetime", "version", "createdAt"}
        assert data["summary"]["createdAt"] == tom_answer_activity_flow.created_at.strftime("%Y-%m-%dT%H:%M:%S.%f")
        assert data["summary"]["version"] == tom_answer_activity_flow.version

        assert set(data["summary"]["identifier"]) == {"lastAnswerDate", "identifier", "userPublicKey"}
        assert data["summary"]["identifier"]["identifier"] == "encrypted_identifier"
        # fmt: on

    async def test_flow_submission_no_flow(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_no_flow
    ):
        client.login(tom)
        url = self.flow_submission_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
            submit_id=tom_answer_activity_no_flow.submit_id,
        )
        response = await client.get(url)
        assert response.status_code == 404

    async def test_summary_for_activity_flow_with_answer(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer, tom_answer_activity_flow
    ):
        client.login(tom)
        url = self.summary_activity_flows_url.format(applet_id=applet_with_flow.id)
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload

        # TODO need proper ordering
        flow_id = str(applet_with_flow.activity_flows[0].id)
        flow_data = None
        for row in payload["result"]:
            if row["id"] == flow_id:
                flow_data = row
                break
        assert flow_data
        assert flow_data["name"] == applet_with_flow.activity_flows[0].name
        assert flow_data["hasAnswer"] is True

    async def test_summary_for_activity_flow_without_answer(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer
    ):
        client.login(tom)
        url = self.summary_activity_flows_url.format(applet_id=applet_with_flow.id)
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert payload["count"] == len(applet_with_flow.activity_flows)

        # TODO need proper ordering
        flow_id = str(applet_with_flow.activity_flows[0].id)
        flow_data = None
        for row in payload["result"]:
            if row["id"] == flow_id:
                flow_data = row
                break
        assert flow_data
        assert flow_data["name"] == applet_with_flow.activity_flows[0].name
        assert flow_data["hasAnswer"] is False

    async def test_get_flow_submissions(
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow, session
    ):
        client.login(tom)
        url = self.flow_submissions_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
        )

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject
        response = await client.get(url, dict(targetSubjectId=tom_subject.id))
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"result", "count"}
        assert data["count"] == 1
        data = data["result"]
        assert set(data.keys()) == {"flows", "submissions"}

        assert len(data["submissions"]) == 1
        submission_data = data["submissions"][0]
        assert set(submission_data.keys()) == {
            "answers",
            "appletId",
            "createdAt",
            "endDatetime",
            "flowHistoryId",
            "isCompleted",
            "submitId",
            "version",
        }
        assert submission_data["submitId"] == str(tom_answer_activity_flow.submit_id)
        answer_data = submission_data["answers"][0]
        assert answer_data["flowHistoryId"] == str(tom_answer_activity_flow.flow_history_id)

        assert len(data["flows"]) == 1
        flow_data = data["flows"][0]
        # fmt: off
        assert set(flow_data.keys()) == {
            "id", "activities", "createdAt", "description", "hideBadge", "idVersion", "isHidden", "isSingleReport",
            "name", "order", "reportIncludedActivityName", "reportIncludedItemName"
        }
        assert len(flow_data["activities"]) == len(applet_with_flow.activity_flows[0].items)
        assert set(flow_data["activities"][0].keys()) == {
            "createdAt", "isSkippable", "showAllAtOnce", "subscaleSetting", "order", "name", "isHidden",
            "scoresAndReports", "isReviewable", "idVersion", "items", "performanceTaskType", "responseIsEditable",
            "appletId", "reportIncludedItemName", "description", "id", "splashScreen", "image"
        }
        assert len(flow_data["activities"][0]["items"]) == len(applet_with_flow.activities[0].items)
        assert set(flow_data["activities"][0]["items"][0].keys()) == {
            "activityId", "allowEdit", "conditionalLogic", "config", "id", "idVersion", "isHidden", "name", "order",
            "question", "responseType", "responseValues"
        }
        # fmt: on
        assert flow_data["idVersion"] == tom_answer_activity_flow.flow_history_id

    @pytest.mark.parametrize(
        "query_params",
        (
            dict(identifiers="nothing"),
            dict(versions="0.0.0"),
            dict(targetSubjectId=str(uuid.uuid4())),
        ),
    )
    async def test_get_flow_submissions_filters_no_data(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow,
        session,
        query_params,
    ):
        client.login(tom)
        url = self.flow_submissions_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
        )
        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject
        query_params.setdefault("targetSubjectId", tom_subject.id)
        response = await client.get(url, query_params)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert not data["result"]["submissions"]
        assert not data["result"]["flows"]

    @pytest.mark.parametrize(
        "flow_index,query_params,total",
        (
            (0, dict(identifiers="encrypted_identifier"), 1),
            (0, dict(identifiers="encrypted_identifierf1a2"), 1),
            (0, dict(identifiers="encrypted_identifier,encrypted_identifierf1a2"), 2),
            (0, dict(versions="1.1.0"), 2),
            (1, dict(versions="1.1.0"), 1),
            (1, dict(identifiers="encrypted_identifierf2a1"), 1),
        ),
    )
    async def test_get_flow_submissions_filters(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        applet_with_flow_answer_create: list[AppletAnswerCreate],
        tom_answer_activity_flow_multiple,
        session,
        flow_index,
        query_params,
        total,
    ):
        client.login(tom)
        flow_id = applet_with_flow.activity_flows[flow_index].id
        url = self.flow_submissions_url.format(
            applet_id=applet_with_flow.id,
            flow_id=flow_id,
        )
        submissions = defaultdict(list)
        for answer in applet_with_flow_answer_create:
            if answer.flow_id != flow_id:
                continue
            if versions := query_params.get("versions"):
                if answer.version not in versions.split(","):
                    continue
            submissions[answer.submit_id].append(answer)
        # apply filters
        filtered_submissions = {}
        for submit_id, _answers in submissions.items():
            if identifiers := query_params.get("identifiers"):
                if not any(a.answer.identifier in identifiers.split(",") for a in _answers):
                    continue
            filtered_submissions[submit_id] = _answers

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject
        query_params.setdefault("targetSubjectId", tom_subject.id)
        response = await client.get(url, query_params)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == total
        assert data["count"] == len(filtered_submissions)
        assert len(data["result"]["submissions"]) == data["count"]
        for s in data["result"]["submissions"]:
            submit_id = uuid.UUID(s["submitId"])
            assert submit_id in filtered_submissions
            assert len(filtered_submissions[submit_id]) == len(s["answers"])

    @pytest.mark.usefixtures("applet_one_lucy_reviewer")
    async def test_get_summary_activity_list_admin_with_role_reviewer_and_any_other_manager_role_can_view_summary(
        self, client: TestClient, applet_one: AppletFull, lucy: User, tom: User, tom_applet_subject: Subject
    ):
        client.login(lucy)
        resp = await client.get(
            self.summary_activities_url.format(applet_id=applet_one.id),
            query={"targetSubjectId": tom_applet_subject.id},
        )
        assert resp.status_code == http.HTTPStatus.OK

    @pytest.mark.usefixtures("applet_one_lucy_reviewer")
    @pytest.mark.usefixtures("applet_one_lucy_coordinator")
    async def test_get_summary_activity_list_role_reviewer_and_coordinator(
        self, client: TestClient, applet_one: AppletFull, lucy: User, tom: User, tom_applet_subject: Subject
    ):
        client.login(lucy)
        resp = await client.get(
            self.summary_activities_url.format(applet_id=applet_one.id),
            query={"targetSubjectId": tom_applet_subject.id},
        )
        assert resp.status_code == http.HTTPStatus.OK

    @pytest.mark.parametrize(
        "role,expected",
        (
            (Role.OWNER, http.HTTPStatus.OK),
            (Role.MANAGER, http.HTTPStatus.OK),
            (Role.REVIEWER, http.HTTPStatus.OK),
            (Role.EDITOR, http.HTTPStatus.FORBIDDEN),
            (Role.COORDINATOR, http.HTTPStatus.FORBIDDEN),
            (Role.RESPONDENT, http.HTTPStatus.FORBIDDEN),
        ),
    )
    async def test_access_to_activity_list(
        self, client, tom: User, user: User, session: AsyncSession, applet, role, expected
    ):
        client.login(tom)
        applet_id = applet.id

        access_service = UserAppletAccessService(session, tom.id, applet_id)
        await access_service.add_role(user.id, role)

        url = self.summary_activities_url.format(applet_id=f"{applet_id}")
        if role == Role.REVIEWER:
            subject = await SubjectsService(session, tom.id).create(
                SubjectCreate(
                    applet_id=applet_id,
                    creator_id=tom.id,
                    first_name="first_name",
                    last_name="last_name",
                    secret_user_id=f"{uuid.uuid4()}",
                )
            )
            assert subject.id
            await access_service.set_subjects_for_review(user.id, applet_id, [subject.id])
            url = f"{url}?targetSubjectId={subject.id}"
        client.login(user)
        response = await client.get(url)
        assert response.status_code == expected
