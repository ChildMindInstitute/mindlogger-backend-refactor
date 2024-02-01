import datetime
import json

from sqlalchemy import select

from apps.answers.db.schemas import AnswerSchema
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from infrastructure.utility import RedisCacheTest


class TestAnswerActivityItems(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "applets/fixtures/applet_histories.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
        "activity_flows/fixtures/activity_flows.json",
        "activity_flows/fixtures/activity_flow_items.json",
        "activities/fixtures/activity_histories.json",
        "activities/fixtures/activity_item_histories.json",
        "activity_flows/fixtures/activity_flow_histories.json",
        "activity_flows/fixtures/activity_flow_item_histories.json",
        "workspaces/fixtures/workspaces.json",
    ]

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
    applet_answers_completions_url = "/answers/applet/{applet_id}/completions"
    applets_answers_completions_url = "/answers/applet/completions"
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

    async def test_answer_activity_items_create_for_respondent(
        self, mock_kiq_report, client
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            version="1.0.0",
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
                scheduledEventId="eventId",
                localEndDate="2022-10-01",
                localEndTime="12:35:00",
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

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        mock_kiq_report.assert_awaited_once()

        published_values = await RedisCacheTest().get(
            "channel_7484f34a-3acc-4ee6-8a94-fd7299502fa1"
        )
        published_values = published_values or []
        assert len(published_values) == 1
        assert len(RedisCacheTest()._storage) == 2
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].subject == "Response alert"

    async def test_get_latest_summary(
        self, mock_report_server_response, mock_kiq_report, client
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            version="1.0.0",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()
        response = await client.post(
            self.latest_report_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            ),
        )
        assert response.status_code == 200

    async def test_public_answer_activity_items_create_for_respondent(
        self, mock_kiq_report, client
    ):
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.public_answer_url, data=create_data)

        assert response.status_code == 201, response.json()

    async def test_answer_skippable_activity_items_create_for_respondent(
        self, mock_kiq_report, client
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            version="1.0.0",
            answer=dict(
                start_time=1690188679657,
                end_time=1690188731636,
                itemIds=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0012",
                ],
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
            self.applet_submit_dates_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    async def test_list_submit_dates(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            version="1.0.0",
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

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        response = await client.get(
            self.applet_submit_dates_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    async def test_answer_flow_items_create_for_respondent(
        self, mock_kiq_report, client
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            created_at=1690188731636,
            flow_id="3013dfb1-9202-4577-80f2-ba7450fb5831",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

    async def test_answer_with_skipping_all(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            version="1.0.0",
            created_at=1690188731636,
            answer=dict(
                start_time=1690188679657,
                end_time=1690188731636,
                itemIds=[
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0012",
                ],
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

    async def test_answered_applet_activities(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.activity_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            )
        )

        assert response.status_code == 200, response.json()

        response = await client.get(
            self.activity_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            )
        )

        assert response.status_code == 200, response.json()
        assert (
            response.json()["result"]["events"]
            == '{"events": ["event1", "event2"]}'
        )

    async def test_fail_answered_applet_not_existed_activities(
        self, mock_kiq_report, client
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.activity_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="00000000-0000-0000-0000-000000000000",
            )
        )

        assert response.status_code == 404, response.json()

    async def test_applet_activity_answers(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answers_for_activity_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    async def test_applet_assessment_retrieve(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()

    async def test_applet_assessment_create(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    "09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.0.0"
                ),
            ),
        )

        assert response.status_code == 201

        response = await client.get(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
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

        response = await client.post(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    "09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.0.0"
                ),
            ),
        )

        assert response.status_code == 201

        response = await client.get(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
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
        response = await client.get(
            self.answer_reviews_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
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
        assert response.json()["result"][0]["reviewer"]["firstName"] == "Tom"
        assert response.json()["result"][0]["reviewer"]["lastName"] == "Isaak"

    async def test_applet_activities(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 0

    async def test_add_note(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.answer_notes_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answer_notes_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    async def test_edit_note(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.answer_notes_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answer_notes_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note"

        response = await client.put(
            self.answer_note_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
                note_id=response.json()["result"][0]["id"],
            ),
            dict(note="Some note 2"),
        )
        assert response.status_code == 200

        response = await client.get(
            self.answer_notes_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note 2"

    async def test_delete_note(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.answer_notes_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answer_notes_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note"

        response = await client.delete(
            self.answer_note_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
                note_id=response.json()["result"][0]["id"],
            )
        )
        assert response.status_code == 204

        response = await client.get(
            self.answer_notes_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 0

    async def test_answer_activity_items_create_for_not_respondent(
        self, mock_kiq_report, client
    ):
        await client.login(self.login_url, "patric@gmail.com", "Test1234")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 403, response.json()

    async def test_answers_export(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        # create answer
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201

        # get answer id
        response = await client.get(
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # create assessment
        response = await client.post(
            self.assessment_answers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    "09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.0.0"
                ),
            ),
        )

        assert response.status_code == 201

        # test export
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
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
        }
        assert int(answer['startDatetime'] * 1000) == 1690188679657
        # fmt: on

        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer["id"]

        # test filters
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
            dict(
                respondentIds="7484f34a-3acc-4ee6-8a94-000000000000",
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        assert not data["answers"]

    async def test_get_identifiers(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.identifiers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 0

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.identifiers_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["identifier"] == "some identifier"
        assert response.json()["result"][0]["userPublicKey"] == "user key"

    async def test_get_versions(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.versions_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert response.json()["result"][0]["version"] == "1.0.0"
        assert response.json()["result"][0]["createdAt"]
        assert response.json()["result"][1]["version"] == "1.9.9"
        assert response.json()["result"][1]["createdAt"]

    async def test_get_summary_activities(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.summary_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == "Flanker"
        assert response.json()["result"][0]["isPerformanceTask"]
        assert not response.json()["result"][0]["hasAnswer"]

    async def test_get_summary_activities_after_submitted_answer(
        self, mock_kiq_report, client
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201

        response = await client.get(
            self.summary_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == "Flanker"
        assert response.json()["result"][0]["isPerformanceTask"]
        assert response.json()["result"][0]["hasAnswer"]

    async def test_store_client_meta(self, mock_kiq_report, client, session):
        app_id = "mindlogger-mobile"
        app_version = "0.21.48"
        app_width = 819
        app_height = 1080

        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

    async def test_activity_answers_by_identifier(
        self, mock_kiq_report, client
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answers_for_activity_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
            query={"emptyIdentifiers": False, "identifiers": "encrypted"},
        )

        assert response.status_code == 200, response.json()
        result = response.json()
        assert result["count"] == 1

    async def test_applet_completions(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        # create answer
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # test completions
        response = await client.get(
            self.applet_answers_completions_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
            {"fromDate": "2022-10-01", "version": "1.0.0"},
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

    async def test_applets_completions(self, mock_kiq_report, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        # create answer
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
            self.review_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
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

        assert response.status_code == 200, response.json()
        data = sorted(response.json()["result"], key=lambda x: x["id"])

        assert len(data) == 2
        apppet_0 = data[0]
        apppet_1 = data[1]

        assert set(apppet_0.keys()) == {
            "id",
            "version",
            "activities",
            "activityFlows",
        }
        assert apppet_0["id"] == "92917a56-d586-4613-b7aa-991f2c4b15b1"
        assert apppet_0["version"] == "1.0.0"
        assert len(apppet_0["activities"]) == 1
        activity_answer_data = apppet_0["activities"][0]
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

        assert set(apppet_1.keys()) == {
            "id",
            "version",
            "activities",
            "activityFlows",
        }
        assert apppet_1["id"] == "92917a56-d586-4613-b7aa-991f2c4b15b2"
        assert apppet_1["version"] == "2.0.1"
        assert len(apppet_1["activities"]) == 0

    async def test_summary_restricted_for_reviewer_if_external_respondent(
        self,
        mock_kiq_report,
        client,
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201

        await client.logout()
        await client.login(self.login_url, "reviewer@mail.com", "Test1234!")

        response = await client.get(
            self.summary_activities_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            )
        )

        assert response.status_code == 403

    async def test_public_answer_with_zero_timestamps(
        self, mock_kiq_report, client
    ):
        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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

        assert response.status_code == 201, response.json()
