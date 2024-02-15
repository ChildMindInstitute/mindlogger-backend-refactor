import datetime
import json
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AnswerSchema
from infrastructure.utility import RedisCacheTest


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


class TestAnswerActivityItems:
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

    activity_answers_url = "/answers/applet/{applet_id}/answers/" "{answer_id}/activities/{activity_id}"
    assessment_answers_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment"

    answer_reviews_url = "/answers/applet/{applet_id}/answers/{answer_id}/reviews"  # noqa: E501
    answer_notes_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes"  # noqa: E501
    answer_note_detail_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes/{note_id}"  # noqa: E501
    latest_report_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{respondent_id}/latest_report"  # noqa: E501

    arbitrary_url = "postgresql+asyncpg://postgres:postgres@localhost:5432" "/test_arbitrary"

    async def test_answer_activity_items_create_for_respondent(
        self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet
    ):
        submit_id = "270d86e0-2158-4d18-befd-86b3ce0122a1"
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")
        create_data = dict(
            submit_id=submit_id,
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
                item_ids=[
                    str(applet.activities[0].items[0].id),
                ],
                identifier="encrypted_identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
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
        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        mock_kiq_report.assert_awaited_once()

        published_values = await RedisCacheTest().get("channel_7484f34a-3acc-4ee6-8a94-fd7299502fa1")
        published_values = published_values or []
        assert len(published_values) == 1
        await assert_answer_exist_on_arbitrary(submit_id, arbitrary_session)
        # TODO: move to the fixtures with yield
        RedisCacheTest._storage = {}

    async def test_get_latest_summary(
        self, mock_report_server_response, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet
    ):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a0",
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce0122a0", arbitrary_session)
        response = await arbitrary_client.post(
            self.latest_report_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa7",
            ),
        )
        assert response.status_code == 200

        response = await arbitrary_client.post(
            self.latest_report_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
                respondent_id="6cde911e-8a57-47c0-b6b2-000000000000",
            ),
        )
        assert response.status_code == 404

    async def test_public_answer_activity_items_create_for_respondent(
        self, mock_kiq_report, arbitrary_session, arbitrary_client, public_applet
    ):
        submit_id = str(uuid.uuid4())
        create_data = dict(
            submit_id=submit_id,
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

        response = await arbitrary_client.post(self.public_answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(submit_id, arbitrary_session)

    async def test_answer_skippable_activity_items_create_for_respondent(
        self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet
    ):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a4",
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            answer=dict(
                start_time=1690188679657,
                end_time=1690188731636,
                itemIds=[
                    "f0ccc10a-2388-48da-a5a1-35e9b19cde5d",
                    "c6fd4e75-c5c1-4a99-89db-4044526b6ad5",
                    "f698d5c6-3861-46a1-a6e7-3bdae7228bce",
                    "8e5ef149-ce10-4590-bc03-594e5200ecb9",
                    "2bcf1de2-aff8-494e-af28-d1ce2602585f",
                ],
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await arbitrary_client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await arbitrary_client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce0122a4", arbitrary_session)

    async def test_list_submit_dates(self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a5",
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
                item_ids=[
                    str(applet.activities[0].items[0].id),
                    "8e5ef149-ce10-4590-bc03-594e5200ecb9",
                ],
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce0122a5", arbitrary_session)

        response = await arbitrary_client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    async def test_answer_flow_items_create_for_respondent(
        self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet
    ):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a6",
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
                item_ids=["2bcf1de2-aff8-494e-af28-d1ce2602585f"],
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce0122a6", arbitrary_session)

        assert response.status_code == 201, response.json()

    async def test_answer_with_skipping_all(self, mock_kiq_report, arbitrary_client, arbitrary_session, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a7",
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            created_at=1690188731636,
            answer=dict(
                start_time=1690188679657,
                end_time=1690188731636,
                itemIds=[
                    "f0ccc10a-2388-48da-a5a1-35e9b19cde5d",
                    "c6fd4e75-c5c1-4a99-89db-4044526b6ad5",
                    "f698d5c6-3861-46a1-a6e7-3bdae7228bce",
                    "8e5ef149-ce10-4590-bc03-594e5200ecb9",
                    "2bcf1de2-aff8-494e-af28-d1ce2602585f",
                ],
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce0122a7", arbitrary_session)

    async def test_answered_applet_activities(self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a8",
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
                item_ids=[
                    "2bcf1de2-aff8-494e-af28-d1ce2602585f",
                    "8e5ef149-ce10-4590-bc03-594e5200ecb9",
                ],
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce0122a8", arbitrary_session)

        response = await arbitrary_client.get(
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
        response = await arbitrary_client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200, response.json()

        response = await arbitrary_client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["events"] == '{"events": ["event1", "event2"]}'

    async def test_fail_answered_applet_not_existed_activities(
        self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet
    ):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a9",
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce0122a9", arbitrary_session)

        response = await arbitrary_client.get(
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
        response = await arbitrary_client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id="00000000-0000-0000-0000-000000000000",
            )
        )

        assert response.status_code == 404, response.json()

    async def test_applet_activity_answers(self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce012210",
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce012210", arbitrary_session)
        response = await arbitrary_client.get(
            self.answers_for_activity_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    async def test_applet_assessment_retrieve(self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce012211",
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
        response = await arbitrary_client.post(self.answer_url, data=create_data)
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce012211", arbitrary_session)

        assert response.status_code == 201, response.json()

        response = await arbitrary_client.get(
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
        response = await arbitrary_client.get(
            self.assessment_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()

    async def test_applet_assessment_create(
        self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet_with_reviewable_activity
    ):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        submit_id = str(uuid.uuid4())
        create_data = dict(
            submit_id=submit_id,
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
                item_ids=[
                    str(applet_with_reviewable_activity.activities[0].items[0].id),
                ],
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(submit_id, arbitrary_session)
        response = await arbitrary_client.get(
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

        response = await arbitrary_client.post(
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

        response = await arbitrary_client.get(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["answer"] == "some answer"
        assert response.json()["result"]["reviewerPublicKey"] == "some public key"
        assert response.json()["result"]["itemIds"] == [str(applet_with_reviewable_activity.activities[0].items[0].id)]

        response = await arbitrary_client.post(
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

        response = await arbitrary_client.get(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["answer"] == "some answer"
        assert response.json()["result"]["reviewerPublicKey"] == "some public key"
        assert response.json()["result"]["itemIds"] == [str(applet_with_reviewable_activity.activities[0].items[0].id)]
        response = await arbitrary_client.get(
            self.answer_reviews_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["answer"] == "some answer"
        assert response.json()["result"][0]["reviewerPublicKey"] == "some public key"
        assert response.json()["result"][0]["itemIds"] == [
            str(applet_with_reviewable_activity.activities[0].items[0].id)
        ]

    async def test_applet_activities(self, mock_kiq_report, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await arbitrary_client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 0

    @pytest.mark.usefixtures("mock_kiq_report", "user")
    async def test_answer_activity_items_create_for_not_respondent(
        self, arbitrary_session, arbitrary_client, public_applet
    ):
        await arbitrary_client.login(self.login_url, "user@example.com", "Test1234!")

        submit_id = str(uuid.uuid4())
        create_data = dict(
            submit_id=submit_id,
            applet_id=str(public_applet.id),
            version=public_applet.version,
            activity_id=str(public_applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        await assert_answer_not_exist_on_arbitrary(submit_id, arbitrary_session)
        assert response.status_code == 403, response.json()

    async def test_answers_export(self, mock_kiq_report, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        # create answer
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)

        assert response.status_code == 201

        # get answer id
        response = await arbitrary_client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # create assessment
        response = await arbitrary_client.post(
            self.assessment_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=("09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.1.0"),
            ),
        )

        assert response.status_code == 201

        # test export
        response = await arbitrary_client.get(
            self.applet_answers_export_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        assert set(data.keys()) == {"answers", "activities"}
        assert len(data["answers"]) == 2

        assessment, answer = data["answers"][0], data["answers"][1]
        # fmt: off
        expected_keys = {
            "activityHistoryId", "activityId", "answer", "appletHistoryId",
            "appletId", "createdAt", "events", "flowHistoryId", "flowId",
            "flowName", "id", "itemIds", "migratedData", "respondentId",
            "respondentSecretId", "reviewedAnswerId", "userPublicKey",
            "version", "submitId", "scheduledDatetime", "startDatetime",
            "endDatetime", "legacyProfileId", "migratedDate", "client",
        }
        assert int(answer['startDatetime'] * 1000) == 1690188679657
        # fmt: on

        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer["id"]

        # test filters
        response = await arbitrary_client.get(
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

    async def test_get_identifiers(self, mock_kiq_report, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await arbitrary_client.get(
            self.identifiers_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 0

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await arbitrary_client.get(
            self.identifiers_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["identifier"] == "some identifier"
        assert response.json()["result"][0]["userPublicKey"] == "user key"

    async def test_get_versions(self, mock_kiq_report, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await arbitrary_client.get(
            self.versions_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["version"] == applet.version
        assert response.json()["result"][0]["createdAt"]

    async def test_get_summary_activities(self, mock_kiq_report, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await arbitrary_client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == applet.activities[0].name
        assert response.json()["result"][0]["isPerformanceTask"] == applet.activities[0].is_performance_task
        assert response.json()["result"][0]["hasAnswer"] is False

    async def test_get_summary_activities_after_submitted_answer(self, mock_kiq_report, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201

        response = await arbitrary_client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == applet.activities[0].name
        assert response.json()["result"][0]["hasAnswer"]

    async def test_store_client_meta(self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet):
        app_id = "mindlogger-mobile"
        app_version = "0.21.48"
        app_width = 819
        app_height = 1080

        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
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
                item_ids=[
                    "2bcf1de2-aff8-494e-af28-d1ce2602585f",
                    str(applet.activities[0].id),
                ],
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
        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201
        db_result = await arbitrary_session.execute(select(AnswerSchema))
        res: AnswerSchema = db_result.scalars().first()
        assert app_id == res.client["app_id"]
        assert app_version == res.client["app_version"]
        assert app_width == res.client["width"]
        assert app_height == res.client["height"]

    async def test_activity_answers_by_identifier(self, mock_kiq_report, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        response = await arbitrary_client.get(
            self.answers_for_activity_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            ),
            query={"identifiers": "encrypted", "emptyIdentifiers": False},
        )
        assert response.status_code == 200, response.json()
        result = response.json()
        assert result["count"] == 1

    async def test_answers_arbitrary_export(self, mock_kiq_report, arbitrary_session, arbitrary_client, tom, applet):
        await arbitrary_client.login(self.login_url, tom.email_encrypted, "Test1234!")

        # create answer
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce012222",
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

        response = await arbitrary_client.post(self.answer_url, data=create_data)
        assert response.status_code == 201
        await assert_answer_exist_on_arbitrary("270d86e0-2158-4d18-befd-86b3ce012222", arbitrary_session)

        # get answer id
        response = await arbitrary_client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # create assessment
        response = await arbitrary_client.post(
            self.assessment_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=("09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.1.0"),
            ),
        )

        assert response.status_code == 201

        # test export
        response = await arbitrary_client.get(
            self.applet_answers_export_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        assert set(data.keys()) == {"answers", "activities"}
        assert len(data["answers"]) == 2

        assessment, answer = data["answers"][0], data["answers"][1]
        # fmt: off
        expected_keys = {
            "activityHistoryId", "activityId", "answer", "appletHistoryId",
            "appletId", "createdAt", "events", "flowHistoryId", "flowId",
            "flowName", "id", "itemIds", "migratedData", "respondentId",
            "respondentSecretId", "reviewedAnswerId", "userPublicKey",
            "version", "submitId", "scheduledDatetime", "startDatetime",
            "endDatetime", "legacyProfileId", "migratedDate", "client",
        }
        assert int(answer['startDatetime'] * 1000) == 1690188679657
        # fmt: on

        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer["id"]

        # test filters
        response = await arbitrary_client.get(
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
