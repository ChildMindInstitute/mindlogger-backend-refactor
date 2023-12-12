import datetime
import json
import uuid

from asynctest import CoroutineMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AnswerSchema
from apps.shared.test import BaseTest
from infrastructure.database import (
    get_specific_session,
    rollback,
    rollback_with_session,
)
from infrastructure.utility import RedisCacheTest


async def get_arbitrary_session():
    url = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/test_arbitrary"
    )
    session = await anext(get_specific_session(url))
    yield session


async def get_answer_by_submit_id(
    submit_id: uuid.UUID, session: AsyncSession
) -> AnswerSchema | None:
    query: Query = select(AnswerSchema)
    query = query.filter(AnswerSchema.submit_id == submit_id)
    result = await session.execute(query)
    return result.scalars().all()


async def assert_answer_exist_on_arbitrary(submit_id: str):
    session = await anext(get_arbitrary_session())
    answer = await get_answer_by_submit_id(uuid.UUID(submit_id), session)
    assert answer


async def assert_answer_not_exist_on_arbitrary(submit_id: str):
    session = await anext(get_arbitrary_session())
    answer = await get_answer_by_submit_id(uuid.UUID(submit_id), session)
    assert not answer


class TestAnswerActivityItems(BaseTest):
    fixtures = ["answers/fixtures/arbitrary_server_answers.json"]

    login_url = "/auth/login"
    answer_url = "/answers"
    public_answer_url = "/public/answers"

    review_activities_url = "/answers/applet/{applet_id}/review/activities"

    summary_activities_url = "/answers/applet/{applet_id}/summary/activities"
    identifiers_url = f"{summary_activities_url}/{{activity_id}}/identifiers"
    versions_url = f"{summary_activities_url}/{{activity_id}}/versions"

    answers_for_activity_url = (
        "/answers/applet/{applet_id}/activities/{activity_id}/answers"
    )
    applet_answers_export_url = "/answers/applet/{applet_id}/data"
    applet_submit_dates_url = "/answers/applet/{applet_id}/dates"

    activity_answers_url = (
        "/answers/applet/{applet_id}/answers/"
        "{answer_id}/activities/{activity_id}"
    )
    assessment_answers_url = (
        "/answers/applet/{applet_id}/answers/{answer_id}/assessment"
    )

    answer_reviews_url = (
        "/answers/applet/{applet_id}/answers/{answer_id}/reviews"  # noqa: E501
    )
    answer_notes_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes"  # noqa: E501
    answer_note_detail_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes/{note_id}"  # noqa: E501
    latest_report_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{respondent_id}/latest_report"  # noqa: E501

    arbitrary_url = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432"
        "/test_arbitrary"
    )

    @patch("apps.answers.service.create_report.kiq")
    @rollback
    async def test_answer_activity_items_create_for_respondent(
        self, report_mock: CoroutineMock
    ):
        submit_id = "270d86e0-2158-4d18-befd-86b3ce0122a1"
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            submit_id=submit_id,
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            version="1.1.0",
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                events=json.dumps(dict(events=["event1", "event2"])),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
                ],
                identifier="encrypted_identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            alerts=[
                dict(
                    activity_item_id="a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
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
        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        report_mock.assert_awaited_once()

        published_values = await RedisCacheTest().get(
            "channel_6cde911e-8a57-47c0-b6b2-685b3664f418"
        )
        published_values = published_values or []
        assert len(published_values) == 1
        await assert_answer_exist_on_arbitrary(submit_id)

    @patch("aiohttp.ClientSession.post")
    @rollback
    async def test_get_latest_summary(self, mock: CoroutineMock):
        mock.return_value.__aenter__.return_value.status = 200
        mock.return_value.__aenter__.return_value.json = CoroutineMock(
            side_effect=lambda: dict(
                pdf="cGRmIGJvZHk=",
                email=dict(
                    body="Body",
                    subject="Subject",
                    attachment="Attachment name",
                    emailRecipients=["tom@cmiml.net"],
                ),
            )
        )

        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a0",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            version="1.1.0",
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                events=json.dumps(dict(events=["event1", "event2"])),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
                ],
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce0122a0"
        )
        response = await self.client.post(
            self.latest_report_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            ),
        )
        assert response.status_code == 200

    @rollback
    async def test_public_answer_activity_items_create_for_respondent(self):
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a3",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
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

        response = await self.client.post(
            self.public_answer_url, data=create_data
        )
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce0122a3"
        )

    @rollback
    async def test_answer_skippable_activity_items_create_for_respondent(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a4",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            version="1.1.0",
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

        response = await self.client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_submit_dates_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8"
            ),
            dict(
                respondentId="6cde911e-8a57-47c0-b6b2-685b3664f418",
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce0122a4"
        )

    @rollback
    async def test_list_submit_dates(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a5",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            version="1.1.0",
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce0122a5"
        )

        response = await self.client.get(
            self.applet_submit_dates_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8"
            ),
            dict(
                respondentId="6cde911e-8a57-47c0-b6b2-685b3664f418",
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    @rollback
    async def test_answer_flow_items_create_for_respondent(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a6",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            created_at=1690188731636,
            flow_id="3013dfb1-9202-4577-80f2-ba7450fb5831",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "2bcf1de2-aff8-494e-af28-d1ce2602585f",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
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

        response = await self.client.post(self.answer_url, data=create_data)
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce0122a6"
        )

        assert response.status_code == 201, response.json()

    @rollback
    async def test_answer_with_skipping_all(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a7",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            version="1.1.0",
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce0122a7"
        )

    @rollback
    async def test_answered_applet_activities(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a8",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce0122a8"
        )

        response = await self.client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8"
            ),
            dict(
                respondentId="6cde911e-8a57-47c0-b6b2-685b3664f418",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await self.client.get(
            self.activity_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            )
        )

        assert response.status_code == 200, response.json()

        response = await self.client.get(
            self.activity_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            )
        )

        assert response.status_code == 200, response.json()
        assert (
            response.json()["result"]["events"]
            == '{"events": ["event1", "event2"]}'
        )

    @rollback
    async def test_fail_answered_applet_not_existed_activities(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122a9",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce0122a9"
        )

        response = await self.client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8"
            ),
            dict(
                respondentId="6cde911e-8a57-47c0-b6b2-685b3664f418",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await self.client.get(
            self.activity_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
                activity_id="00000000-0000-0000-0000-000000000000",
            )
        )

        assert response.status_code == 404, response.json()

    @patch("apps.answers.service.create_report.kiq")
    @rollback
    async def test_applet_activity_answers(self, report_mock: CoroutineMock):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce012210",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce012210"
        )
        response = await self.client.get(
            self.answers_for_activity_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    @rollback
    async def test_applet_assessment_retrieve(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce012211",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
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
        response = await self.client.post(self.answer_url, data=create_data)
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce012211"
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8"
            ),
            dict(
                respondentId="6cde911e-8a57-47c0-b6b2-685b3664f418",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await self.client.get(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()

    @rollback
    async def test_applet_assessment_create(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce012212",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "c6fd4e75-c5c1-4a99-89db-4044526b6a85",
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce012212"
        )
        response = await self.client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8"
            ),
            dict(
                respondentId="6cde911e-8a57-47c0-b6b2-685b3664f418",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await self.client.post(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["f0ccc10a-2388-48da-a5a1-35e9b19cde5d"],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    "09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.1.0"
                ),
            ),
        )

        assert response.status_code == 201

        response = await self.client.get(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["answer"] == "some answer"
        assert (
            response.json()["result"]["reviewerPublicKey"] == "some public key"
        )
        assert response.json()["result"]["itemIds"] == [
            "f0ccc10a-2388-48da-a5a1-35e9b19cde5d"
        ]

        response = await self.client.post(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    "09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.1.0"
                ),
            ),
        )

        assert response.status_code == 201

        response = await self.client.get(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["answer"] == "some answer"
        assert (
            response.json()["result"]["reviewerPublicKey"] == "some public key"
        )
        assert response.json()["result"]["itemIds"] == [
            "a18d3409-2c96-4a5e-a1f3-1c1c14be0021"
        ]
        response = await self.client.get(
            self.answer_reviews_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["answer"] == "some answer"
        assert (
            response.json()["result"][0]["reviewerPublicKey"]
            == "some public key"
        )
        assert response.json()["result"][0]["itemIds"] == [
            "a18d3409-2c96-4a5e-a1f3-1c1c14be0021"
        ]

    @rollback
    async def test_applet_activities(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8"
            ),
            dict(
                respondentId="6cde911e-8a57-47c0-b6b2-685b3664f418",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 0

    @rollback
    async def test_answer_activity_items_create_for_not_respondent(self):
        await self.client.login(self.login_url, "patric@gmail.com", "Test1234")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce012213",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
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

        response = await self.client.post(self.answer_url, data=create_data)
        await assert_answer_not_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce012213"
        )
        assert response.status_code == 403, response.json()

    @rollback
    async def test_answers_export(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        # create answer
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
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

        response = await self.client.post(self.answer_url, data=create_data)

        assert response.status_code == 201

        # get answer id
        response = await self.client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8"
            ),
            dict(
                respondentId="6cde911e-8a57-47c0-b6b2-685b3664f418",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # create assessment
        response = await self.client.post(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    "09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.1.0"
                ),
            ),
        )

        assert response.status_code == 201

        # test export
        response = await self.client.get(
            self.applet_answers_export_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
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
            "endDatetime", "legacyProfileId", "migratedDate"
        }
        assert int(answer['startDatetime'] * 1000) == 1690188679657
        # fmt: on

        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer["id"]

        # test filters
        response = await self.client.get(
            self.applet_answers_export_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            ),
            dict(
                respondentIds="7484f34a-3acc-4ee6-8a94-000000000000",
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        assert not data["answers"]

    @rollback
    async def test_get_identifiers(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.identifiers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 0

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
                ],
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

        response = await self.client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.identifiers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["identifier"] == "some identifier"
        assert response.json()["result"][0]["userPublicKey"] == "user key"

    @rollback
    async def test_get_versions(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.versions_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["version"] == "1.1.0"
        assert response.json()["result"][0]["createdAt"]

    @rollback
    async def test_get_summary_activities(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.summary_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == "PHQ2"
        assert response.json()["result"][0]["isPerformanceTask"] is False
        assert response.json()["result"][0]["hasAnswer"] is False

    @rollback
    async def test_get_summary_activities_after_submitted_answer(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
                ],
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201

        response = await self.client.get(
            self.summary_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == "PHQ2"
        assert response.json()["result"][0]["hasAnswer"]

    @rollback_with_session
    async def test_store_client_meta(self, **kwargs):
        session = kwargs["session"]
        app_id = "mindlogger-mobile"
        app_version = "0.21.48"
        app_width = 819
        app_height = 1080

        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "2bcf1de2-aff8-494e-af28-d1ce2602585f",
                    "09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
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
        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201
        res = await session.execute(select(AnswerSchema))
        res: AnswerSchema = res.scalars().first()
        assert app_id == res.client["app_id"]
        assert app_version == res.client["app_version"]
        assert app_width == res.client["width"]
        assert app_height == res.client["height"]

    @patch("apps.answers.service.create_report.kiq")
    @rollback
    async def test_activity_answers_by_identifier(
        self, report_mock: CoroutineMock
    ):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
                ],
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
        response = await self.client.get(
            self.answers_for_activity_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            ),
            query={"identifiers": "encrypted", "emptyIdentifiers": False},
        )
        assert response.status_code == 200, response.json()
        result = response.json()
        assert result["count"] == 1

    @rollback
    async def test_answers_arbitrary_export(self):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )

        # create answer
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce012222",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            version="1.1.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3618",
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        additional_text=None,
                    )
                ),
                item_ids=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
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

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201
        await assert_answer_exist_on_arbitrary(
            "270d86e0-2158-4d18-befd-86b3ce012222"
        )

        # get answer id
        response = await self.client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8"
            ),
            dict(
                respondentId="6cde911e-8a57-47c0-b6b2-685b3664f418",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # create assessment
        response = await self.client.post(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    "09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.1.0"
                ),
            ),
        )

        assert response.status_code == 201

        # test export
        response = await self.client.get(
            self.applet_answers_export_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
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
            "endDatetime", "legacyProfileId", "migratedDate"
        }
        assert int(answer['startDatetime'] * 1000) == 1690188679657
        # fmt: on

        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer["id"]

        # test filters
        response = await self.client.get(
            self.applet_answers_export_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
            ),
            dict(
                respondentIds="7484f34a-3acc-4ee6-8a94-000000000000",
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        assert not data["answers"]
