import datetime
import json
import re
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.crud import AnswerItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.db.schemas import AnswerItemSchema, AnswerSchema
from apps.answers.domain import AppletAnswerCreate, AssessmentAnswerCreate, ClientMeta, ItemAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain.applet_full import AppletFull
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.users import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.utility import RedisCacheTest


@pytest.fixture
async def bob_reviewer_in_applet_with_reviewable_activity(session, tom, bob, applet_with_reviewable_activity) -> User:
    await UserAppletAccessCRUD(session).save(
        UserAppletAccessSchema(
            user_id=bob.id,
            applet_id=applet_with_reviewable_activity.id,
            role=Role.REVIEWER,
            owner_id=tom.id,
            invitor_id=tom.id,
            meta=dict(respondents=[str(tom.id)]),
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
async def tom_answer_item_for_applet(tom: User, applet: AppletFull, session: AsyncSession):
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
async def tom_answer_activity_flow_multiple(
    session: AsyncSession, tom: User, applet_with_flow: AppletFull
) -> list[AnswerSchema]:
    answer_service = AnswerService(session, tom.id)
    submit_id = uuid.uuid4()
    answer_data = dict(
        applet_id=applet_with_flow.id,
        version=applet_with_flow.version,
        client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
    )
    answer_item_data = dict(
        start_time=datetime.datetime.utcnow(),
        end_time=datetime.datetime.utcnow(),
        user_public_key=str(tom.id),
        identifier="encrypted_identifier",
    )
    answers = [
        # flow#1 submission#1
        await answer_service.create_answer(
            AppletAnswerCreate(
                submit_id=uuid.uuid4(),
                flow_id=applet_with_flow.activity_flows[0].id,
                is_flow_completed=True,
                activity_id=applet_with_flow.activities[0].id,
                answer=ItemAnswerCreate(item_ids=[applet_with_flow.activities[0].items[0].id], **answer_item_data),
                **answer_data,
            )
        ),
        # flow#2 submission#1
        await answer_service.create_answer(
            AppletAnswerCreate(
                submit_id=submit_id,
                flow_id=applet_with_flow.activity_flows[1].id,
                is_flow_completed=False,
                activity_id=applet_with_flow.activities[0].id,
                answer=ItemAnswerCreate(item_ids=[applet_with_flow.activities[0].items[0].id], **answer_item_data),
                **answer_data,
            )
        ),
        await answer_service.create_answer(
            AppletAnswerCreate(
                submit_id=submit_id,
                flow_id=applet_with_flow.activity_flows[1].id,
                is_flow_completed=False,
                activity_id=applet_with_flow.activities[1].id,
                answer=ItemAnswerCreate(item_ids=[applet_with_flow.activities[1].items[0].id], **answer_item_data),
                **answer_data,
            )
        ),
        # flow#1 submission#2
        await answer_service.create_answer(
            AppletAnswerCreate(
                submit_id=uuid.uuid4(),
                flow_id=applet_with_flow.activity_flows[0].id,
                is_flow_completed=True,
                activity_id=applet_with_flow.activities[0].id,
                answer=ItemAnswerCreate(item_ids=[applet_with_flow.activities[0].items[0].id], **answer_item_data),
                **answer_data,
            )
        ),
    ]
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
    identifiers_url = f"{summary_activities_url}/{{activity_id}}/identifiers"
    versions_url = f"{summary_activities_url}/{{activity_id}}/versions"

    answers_for_activity_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers"
    applet_answers_export_url = "/answers/applet/{applet_id}/data"
    applet_answers_completions_url = "/answers/applet/{applet_id}/completions"
    applets_answers_completions_url = "/answers/applet/completions"
    applet_submit_dates_url = "/answers/applet/{applet_id}/dates"

    activity_answers_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{answer_id}"
    flow_submission_url = "/answers/applet/{applet_id}/flows/{flow_id}/submissions/{submit_id}"
    assessment_answers_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment"

    answer_reviews_url = "/answers/applet/{applet_id}/answers/{answer_id}/reviews"  # noqa: E501
    answer_notes_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes"  # noqa: E501
    answer_note_detail_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes/{note_id}"  # noqa: E501
    latest_report_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{respondent_id}/latest_report"  # noqa: E501
    assessment_delete_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment/{assessment_id}"

    async def test_answer_activity_items_create_for_respondent(self, mock_kiq_report, client, tom, applet: AppletFull):
        client.login(tom)
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                events=json.dumps(dict(events=["event1", "event2"])),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="encrypted_identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
                scheduledEventId="eventId",
                localEndDate="2022-10-01",
                localEndTime="12:35:00",
            ),
            alerts=[
                dict(
                    activity_item_id=str(applet.activities[0].items[0].id),
                    message="hello world",
                )
            ],
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        mock_kiq_report.assert_awaited_once()

        published_values = await RedisCacheTest().get(f"channel_{tom.id}")
        published_values = published_values or []
        assert len(published_values) == 1
        # 2 because alert for lucy and for tom
        assert len(RedisCacheTest()._storage) == 1
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].subject == "Response alert"
        # TODO: move to the fixtures with yield
        RedisCacheTest._storage = {}

    async def test_get_latest_summary(self, mock_report_server_response, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                events=json.dumps(dict(events=["event1", "event2"])),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="encrypted_identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()
        response = await client.post(
            self.latest_report_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
                respondent_id=tom.id,
            ),
        )
        assert response.status_code == 200

    async def test_public_answer_activity_items_create_for_respondent(
        self, mock_kiq_report, client, tom, public_applet
    ):
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(public_applet.id),
            version=public_applet.version,
            activity_id=str(public_applet.activities[0].id),
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(public_applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.public_answer_url, data=create_data)

        assert response.status_code == 201, response.json()

    async def test_answer_skippable_activity_items_create_for_respondent(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            answer=dict(
                start_time=1690188679657,
                end_time=1690188731636,
                itemIds=[str(applet.activities[0].items[0].id)],
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    async def test_list_submit_dates(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        response = await client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    async def test_answer_flow_items_create_for_respondent(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            created_at=1690188731636,
            flow_id="3013dfb1-9202-4577-80f2-ba7450fb5831",
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

    async def test_answer_with_skipping_all(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            created_at=1690188731636,
            answer=dict(
                start_time=1690188679657,
                end_time=1690188731636,
                itemIds=[str(applet.activities[0].items[0].id)],
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

    async def test_answered_applet_activities(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
                identifier="encrypted_identifier",
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        assert data["answer"]["events"] == '{"events": ["event1", "event2"]}'
        assert set(data["summary"]["identifier"]) == {"lastAnswerDate", "identifier", "userPublicKey"}
        assert data["summary"]["identifier"]["identifier"] == "encrypted_identifier"

    async def test_fail_answered_applet_not_existed_activities(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id="00000000-0000-0000-0000-000000000000",
            )
        )

        assert response.status_code == 404, response.json()

    async def test_applet_activity_answers(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answers_for_activity_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    async def test_applet_assessment_retrieve(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()

    async def test_applet_assessment_create(self, mock_kiq_report, client, tom, applet_with_reviewable_activity):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet_with_reviewable_activity.id),
            version=applet_with_reviewable_activity.version,
            activity_id=str(applet_with_reviewable_activity.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet_with_reviewable_activity.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet_with_reviewable_activity.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # create assessment
        response = await client.post(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=[str(applet_with_reviewable_activity.activities[0].items[0].id)],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    f"{applet_with_reviewable_activity.activities[0].id}_{applet_with_reviewable_activity.version}"
                ),
            ),
        )

        assert response.status_code == 201

        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            )
        )
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["answer"] == "some answer"
        assert response.json()["result"]["reviewerPublicKey"] == "some public key"
        assert response.json()["result"]["itemIds"] == [str(applet_with_reviewable_activity.activities[0].items[0].id)]

        response = await client.post(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=[str(applet_with_reviewable_activity.activities[0].items[0].id)],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    f"{applet_with_reviewable_activity.activities[0].id}_{applet_with_reviewable_activity.version}"
                ),
            ),
        )

        assert response.status_code == 201

        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["answer"] == "some answer"
        assert response.json()["result"]["reviewerPublicKey"] == "some public key"
        assert response.json()["result"]["itemIds"] == [str(applet_with_reviewable_activity.activities[0].items[0].id)]
        response = await client.get(
            self.answer_reviews_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            )
        )
        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
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
        assert response.json()["result"][0]["answer"] == "some answer"
        assert response.json()["result"][0]["reviewerPublicKey"] == "some public key"
        assert response.json()["result"][0]["itemIds"] == [
            str(applet_with_reviewable_activity.activities[0].items[0].id)
        ]
        assert response.json()["result"][0]["reviewer"]["firstName"] == "Tom"
        assert response.json()["result"][0]["reviewer"]["lastName"] == "Isaak"

    async def test_applet_activities(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 0

    async def test_add_note(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    async def test_edit_note(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note"

        response = await client.put(
            self.answer_note_detail_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
                note_id=response.json()["result"][0]["id"],
            ),
            dict(note="Some note 2"),
        )
        assert response.status_code == 200

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note 2"

    async def test_delete_note(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=None,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note"

        response = await client.delete(
            self.answer_note_detail_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
                note_id=response.json()["result"][0]["id"],
            )
        )
        assert response.status_code == 204

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 0

    @pytest.mark.usefixtures("mock_kiq_report", "user")
    async def test_answer_activity_items_create_for_not_respondent(self, client, applet, user):
        client.login(user)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 403, response.json()

    async def test_answers_export(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        # create answer
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )
        tz_str = "US/Pacific"
        tz_offset = -420

        response = await client.post(
            self.answer_url,
            data=create_data,
            headers={"x-timezone": tz_str},
        )

        assert response.status_code == 201

        # get answer id
        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # create assessment
        response = await client.post(
            self.assessment_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=("09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.0.0"),
            ),
        )

        assert response.status_code == 201

        # test export
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200, response.json()
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
            "endDatetime", "legacyProfileId", "migratedDate", "client",
            "tzOffset", "scheduledEventId",
        }
        assert int(answer["startDatetime"] * 1000) == 1690188679657
        assert answer["tzOffset"] == tz_offset
        assert re.match(
            r"\[admin account\] \([0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12}\)",
            answer["respondentSecretId"]
        )
        # fmt: on

        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer["id"]

        # test filters
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id=str(applet.id),
            ),
            dict(
                respondentIds="7484f34a-3acc-4ee6-8a94-000000000000",
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        assert not data["answers"]

    async def test_get_identifiers(self, mock_kiq_report, client, tom, applet):
        client.login(tom)
        identifier_url = self.identifiers_url.format(applet_id=str(applet.id), activity_id=str(applet.activities[0].id))
        identifier_url = f"{identifier_url}?respondentId={tom.id}"
        response = await client.get(identifier_url)

        assert response.status_code == 200
        assert response.json()["count"] == 0

        created_at = datetime.datetime.utcnow()
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="some identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
            created_at=created_at,
        )
        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(identifier_url)
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["identifier"] == "some identifier"
        assert response.json()["result"][0]["userPublicKey"] == "user key"
        assert datetime.datetime.fromisoformat(response.json()["result"][0]["lastAnswerDate"]) == created_at

    async def test_get_versions(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        response = await client.get(
            self.versions_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["version"] == applet.version
        assert response.json()["result"][0]["createdAt"]

    async def test_get_summary_activities(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == applet.activities[0].name
        assert not response.json()["result"][0]["isPerformanceTask"]
        assert not response.json()["result"][0]["hasAnswer"]

    async def test_get_summary_activities_after_submitted_answer(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="some identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["hasAnswer"]

    async def test_store_client_meta(self, mock_kiq_report, client, session, tom, applet):
        app_id = "mindlogger-mobile"
        app_version = "0.21.48"
        app_width = 819
        app_height = 1080

        client.login(tom)
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="some identifier",
                scheduled_time=10,
                start_time=10,
                end_time=11,
            ),
            client=dict(
                appId=app_id,
                appVersion=app_version,
                width=app_width,
                height=app_height,
            ),
        )
        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201
        db_result = await session.execute(select(AnswerSchema))
        res: AnswerSchema = db_result.scalars().first()
        assert app_id == res.client["app_id"]
        assert app_version == res.client["app_version"]
        assert app_width == res.client["width"]
        assert app_height == res.client["height"]

    async def test_activity_answers_by_identifier(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
                identifier="encrypted",
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answers_for_activity_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            ),
            query={"emptyIdentifiers": False, "identifiers": "encrypted"},
        )

        assert response.status_code == 200, response.json()
        result = response.json()
        assert result["count"] == 1

    async def test_applet_completions(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        # create answer
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
                scheduledEventId="eventId",
                localEndDate="2022-10-01",
                localEndTime="12:35:00",
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201

        # get answer id
        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # test completions
        response = await client.get(
            self.applet_answers_completions_url.format(
                applet_id=str(applet.id),
            ),
            {"fromDate": "2022-10-01", "version": applet.version},
        )

        assert response.status_code == 200, response.json()
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
        assert activity_answer_data["answerId"] == answer_id
        assert activity_answer_data["localEndTime"] == "12:35:00"

    async def test_applets_completions(self, mock_kiq_report, client, tom, applet):
        client.login(tom)

        # create answer
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
                scheduledEventId="eventId",
                localEndDate="2022-10-01",
                localEndTime="12:35:00",
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201

        # get answer id
        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # test completions
        response = await client.get(
            url=self.applets_answers_completions_url,
            query={"fromDate": "2022-10-01"},
        )

        assert response.status_code == 200
        data = response.json()["result"]
        # 2 session applets and 1 for answers
        assert len(data) == 3
        applet_with_answer = next(i for i in data if i["id"] == str(applet.id))

        assert applet_with_answer["id"] == str(applet.id)
        assert applet_with_answer["version"] == applet.version
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
        assert activity_answer_data["answerId"] == answer_id
        assert activity_answer_data["scheduledEventId"] == "eventId"
        assert activity_answer_data["localEndDate"] == "2022-10-01"
        assert activity_answer_data["localEndTime"] == "12:35:00"
        for applet_data in data:
            if applet_data["id"] != str(applet.id):
                assert not applet_data["activities"]
                assert not applet_data["activityFlows"]

    @pytest.mark.usefixtures("user_reviewer_applet_one")
    async def test_summary_restricted_for_reviewer_if_external_respondent(
        self, mock_kiq_report, client, tom, applet_one, user
    ):
        client.login(tom)

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet_one.id),
            version=applet_one.version,
            activity_id=str(applet_one.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet_one.activities[0].items[0].id)],
                identifier="some identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201

        client.logout()
        client.login(user)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_one.id),
            )
        )

        assert response.status_code == 403

    async def test_public_answer_with_zero_start_time_end_time_timestamps(
        self, mock_kiq_report, client, tom, public_applet
    ):
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(public_applet.id),
            version=public_applet.version,
            activity_id=str(public_applet.activities[0].id),
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(public_applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=0,
                end_time=0,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.public_answer_url, data=create_data)

        assert response.status_code == 201

    @pytest.mark.parametrize(
        "user_fixture,expected_code",
        (
            ("tom", 204),  # owner
            ("lucy", 403),  # not in applet
            ("bob", 403),  # reviewer
        ),
    )
    @pytest.mark.usefixtures("bob_reviewer_in_applet_with_reviewable_activity")
    async def test_review_delete(
        self,
        mock_kiq_report,
        client,
        tom,
        applet_with_reviewable_activity,
        session,
        user_fixture,
        expected_code,
        request,
        tom_answer,
        tom_review_answer,
    ):
        login_user = request.getfixturevalue(user_fixture)
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

    async def test_get_all_types_of_identifiers(
        self, mock_kiq_report, client, tom: User, applet: AppletFull, session, tom_answer_item_for_applet, request
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
        assert res.status_code == 200
        payload = res.json()
        assert payload["count"] == len(answer_items)
        for identifier in payload["result"]:
            assert "lastAnswerDate" in identifier
            if identifier["identifier"] in ["encrypted identifier", "identifier"]:
                assert "userPublicKey" in identifier

    async def test_summary_activities_submitted_date_with_answers(
        self,
        mock_kiq_report,
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

    async def test_summary_activities_submitted_without_answers(
        self,
        mock_kiq_report,
        client,
        tom,
        applet_with_reviewable_activity,
        session,
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_id),
            )
        )
        assert response.status_code == 200
        payload = response.json()
        actual_last_date = payload["result"][0]["lastAnswerDate"]
        assert actual_last_date is None

    async def test_answer_reviewer_count_for_multiple_reviews(
        self,
        mock_kiq_report,
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
        url = self.answers_for_activity_url.format(applet_id=str(applet_id), activity_id=str(activity_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload["result"][0]["reviewCount"]["mine"] == 1
        assert payload["result"][0]["reviewCount"]["other"] == 2

    async def test_answer_reviewer_count_for_one_own_review(
        self, mock_kiq_report, client, tom, applet_with_reviewable_activity: AppletFull, tom_answer, tom_review_answer
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        activity_id = applet_with_reviewable_activity.activities[0].id
        url = self.answers_for_activity_url.format(applet_id=str(applet_id), activity_id=str(activity_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload["result"][0]["reviewCount"]["mine"] == 1
        assert payload["result"][0]["reviewCount"]["other"] == 0

    async def test_answer_reviewer_count_for_one_other_review(
        self, mock_kiq_report, client, tom, applet_with_reviewable_activity: AppletFull, tom_answer, bob_review_answer
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        activity_id = applet_with_reviewable_activity.activities[0].id
        url = self.answers_for_activity_url.format(applet_id=str(applet_id), activity_id=str(activity_id))
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
    async def test_owner_can_view_all_reviews(
        self,
        bob_reviewer_in_applet_with_reviewable_activity,
        lucy_manager_in_applet_with_reviewable_activity,
        tom_answer,
        tom_review_answer,
        bob_review_answer,
        mock_kiq_report,
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
        mock_kiq_report,
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
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow
    ):
        client.login(tom)
        url = self.review_flows_url.format(applet_id=applet_with_flow.id)
        response = await client.get(
            url,
            dict(
                respondentId=tom.id,
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
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow_multiple
    ):
        client.login(tom)
        url = self.review_flows_url.format(applet_id=applet_with_flow.id)
        response = await client.get(
            url,
            dict(
                respondentId=tom.id,
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

    async def test_flow_submission(
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow
    ):
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
        assert set(data.keys()) == {"flow", "answers", "summary"}

        assert len(data["answers"]) == len(applet_with_flow.activity_flows[0].items)
        # fmt: off
        assert set(data["answers"][0].keys()) == {
            "activityHistoryId", "activityId", "answer", "createdAt", "endDatetime", "events", "flowHistoryId", "id",
            "identifier", "itemIds", "migratedData", "submitId", "userPublicKey", "version"
        }
        assert data["answers"][0]["submitId"] == str(tom_answer_activity_flow.submit_id)
        assert data["answers"][0]["flowHistoryId"] == str(tom_answer_activity_flow.flow_history_id)

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
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_no_flow
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
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer, tom_answer_activity_flow
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
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer
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
