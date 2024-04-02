import datetime
import http
import re
import uuid
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
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from infrastructure.utility import RedisCacheTest


@pytest.fixture
async def bob_reviewer_in_applet_with_reviewable_activity(session, tom, bob, applet_with_reviewable_activity) -> User:
    applet_id = applet_with_reviewable_activity.id
    await UserAppletAccessService(session, tom.id, applet_id).add_role(bob.id, Role.REVIEWER)
    return bob


@pytest.fixture
def tom_answer_create_data(tom, applet_with_reviewable_activity):
    return AppletAnswerCreate(
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


@pytest.fixture
def tom_answer_assessment_create_data(tom, applet_with_reviewable_activity):
    activity_assessment_id = applet_with_reviewable_activity.activities[1].id
    return AssessmentAnswerCreate(
        answer="0x00",
        item_ids=[applet_with_reviewable_activity.activities[1].items[0].id],
        reviewer_public_key=f"{tom.id}",
        assessment_version_id=f"{activity_assessment_id}_{applet_with_reviewable_activity.version}",
    )


def note_url_path_data(answer: AnswerSchema) -> dict[str, Any]:
    return {
        "applet_id": answer.applet_id,
        "answer_id": answer.id,
        "activity_id": answer.activity_history_id.split("_")[0],
    }


@pytest.fixture
async def tom_answer_item_for_applet(tom, applet, session):
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
        )
    )
    return dict(
        answer_id=answer.id,
        respondent_id=tom.id,
        answer="0x00",
        item_ids=[str(item.id) for item in applet.activities[0].items],
        start_datetime=datetime.datetime.utcnow(),
        end_datetime=datetime.datetime.utcnow(),
        is_assessment=False,
    )


@pytest.mark.usefixtures("mock_kiq_report")
class TestAnswerActivityItems(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]

    login_url = "/auth/login"
    answer_url = "/answers"
    public_answer_url = "/public/answers"

    review_activities_url = "/answers/applet/{applet_id}/review/activities"

    summary_activities_url = "/answers/applet/{applet_id}/summary/activities"
    identifiers_url = f"{summary_activities_url}/{{activity_id}}/identifiers"
    versions_url = f"{summary_activities_url}/{{activity_id}}/versions"

    answers_for_activity_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers"
    applet_answers_export_url = "/answers/applet/{applet_id}/data"
    applet_answers_completions_url = "/answers/applet/{applet_id}/completions"
    applets_answers_completions_url = "/answers/applet/completions"
    applet_submit_dates_url = "/answers/applet/{applet_id}/dates"

    activity_answers_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}"
    assessment_answers_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment"

    answer_reviews_url = "/answers/applet/{applet_id}/answers/{answer_id}/reviews"
    answer_notes_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes"
    answer_note_detail_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes/{note_id}"
    latest_report_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{respondent_id}/latest_report"
    check_existence_url = "/answers/check-existence"
    assessment_delete_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment/{assessment_id}"

    async def test_answer_activity_items_create_for_respondent(
        self,
        mock_kiq_report: AsyncMock,
        client: TestClient,
        tom: User,
        redis: RedisCacheTest,
        answer_with_alert_create: AppletAnswerCreate,
    ):
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_with_alert_create)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        mock_kiq_report.assert_awaited_once()

        published_values = await redis.get(f"channel_{tom.id}")
        published_values = published_values or []
        assert len(published_values) == 1
        # 2 because alert for lucy and for tom
        assert len(redis._storage) == 1
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].subject == "Response alert"

        response = await client.get(
            self.review_activities_url.format(applet_id=str(answer_with_alert_create.applet_id)),
            dict(
                respondentId=tom.id,
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
    async def test_get_latest_summary(self, client: TestClient, tom: User, applet: AppletFull):
        client.login(tom)

        response = await client.post(
            self.latest_report_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
                respondent_id=tom.id,
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

    async def test_answered_applet_activities(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        client.login(tom)

        response = await client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(answer_create.applet_id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(answer_create.applet_id),
                answer_id=answer_id,
                activity_id=str(answer_create.activity_id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["events"] == answer_create.answer.events

    async def test_get_answer_activity(self, client: TestClient, tom: User, applet: AppletFull, answer: AnswerSchema):
        client.login(tom)
        response = await client.get(
            self.activity_answers_url.format(
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
            self.activity_answers_url.format(
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
            self.answers_for_activity_url.format(
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
        assert response.json()["count"] == 1
        review = response.json()["result"][0]
        assert review["answer"] == assessment_create.answer
        assert review["reviewerPublicKey"] == assessment_create.reviewer_public_key
        assert review["itemIds"] == [str(i) for i in assessment_create.item_ids]
        assert review["reviewer"]["firstName"] == tom.first_name
        assert review["reviewer"]["lastName"] == tom.last_name

    async def test_applet_activities(self, client: TestClient, tom: User, answer: AnswerSchema):
        client.login(tom)

        response = await client.get(
            self.review_activities_url.format(applet_id=str(answer.applet_id)),
            dict(
                respondentId=tom.id,
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
            "endDatetime", "legacyProfileId", "migratedDate", "client",
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

    async def test_get_identifiers(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate, applet: AppletFull
    ):
        client.login(tom)
        identifier_url = self.identifiers_url.format(applet_id=str(applet.id), activity_id=str(applet.activities[0].id))
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

    # TODO: Move to another place, not needed any answer for test
    async def test_get_all_activity_versions_for_applet(self, client: TestClient, tom: User, applet: AppletFull):
        client.login(tom)

        response = await client.get(
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

    @pytest.mark.usefixtures("answer")
    async def test_get_summary_activities_has_answer_no_performance_task(
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
            self.answers_for_activity_url.format(
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
    ):
        login_user = request.getfixturevalue(user_fixture_name)
        client.login(login_user)
        answer_service = AnswerService(session, tom.id)
        answer = await answer_service.create_answer(tom_answer_create_data)
        await answer_service.create_assessment_answer(
            applet_with_reviewable_activity.id, answer.id, tom_answer_assessment_create_data
        )
        assessment = await AnswerItemsCRUD(session).get_assessment(answer.id, tom.id)
        assert assessment
        response = await client.delete(
            self.assessment_delete_url.format(
                applet_id=str(applet_with_reviewable_activity.id), answer_id=answer.id, assessment_id=assessment.id
            )
        )
        assert response.status_code == expected_code
        assessment = await AnswerItemsCRUD(session).get_assessment(answer.id, tom.id)
        if expected_code == 204:
            assert not assessment
        else:
            assert assessment

    async def test_summary_activities_submitted_date_with_answers(
        self,
        tom_answer_create_data,
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
            answer = await answer_service.create_answer(tom_answer_create_data)
            submit_dates.append(answer.created_at)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_id),
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        payload = response.json()
        expected_last_date = str(max(submit_dates))
        actual_last_date = payload["result"][0]["lastAnswerDate"].replace("T", " ")
        assert actual_last_date == expected_last_date

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

    async def test_get_all_types_of_identifiers(
        self, client, tom: User, applet: AppletFull, session, tom_answer_item_for_applet, request
    ):
        client.login(tom)
        identifier_url = self.identifiers_url.format(applet_id=str(applet.id), activity_id=str(applet.activities[0].id))
        identifier_url = f"{identifier_url}?respondentId={tom.id}"

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
