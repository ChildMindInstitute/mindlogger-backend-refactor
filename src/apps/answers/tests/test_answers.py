import datetime
import json

import pytest

from apps.shared.test import BaseTest
from infrastructure.database import rollback


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
    ]

    login_url = "/auth/login"
    answer_activity_item_create_url = "/answers"
    public_answer_activity_item_create_url = "/public/answers"
    answered_applet_activities_url = "/answers/applet/{id_}/activities"
    applet_submit_dates_url = "/answers/applet/{id_}/dates"
    activity_answers_url = (
        "/answers/applet/{id_}/answers/{answer_id}/activities/{activity_id}"
    )
    assessment_answers_url = (
        "/answers/applet/{id_}/answers/{answer_id}"
        "/activities/{activity_id}/assessment"
    )
    answer_notes_url = "/answers/applet/{id_}/answers/{answer_id}/activities/{activity_id}/notes"  # noqa: E501
    answer_note_detail_url = "/answers/applet/{id_}/answers/{answer_id}/activities/{activity_id}/notes/{note_id}"  # noqa: E501

    @rollback
    async def test_answer_activity_items_create_for_respondent(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            user_public_key="user key",
            created_at=1681216969,
            answers=[
                dict(
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

    @rollback
    async def test_public_answer_activity_items_create_for_respondent(self):
        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            user_public_key="user key",
            created_at=1681216969,
            answers=[
                dict(
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
                )
            ],
        )

        response = await self.client.post(
            self.public_answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

    @rollback
    async def test_answer_skippable_activity_items_create_for_respondent(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2",
            version="2.0.1",
            user_public_key="user key",
            answers=[],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_submit_dates_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b2"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    @rollback
    async def test_list_submit_dates(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            user_public_key="user key",
            answers=[
                dict(
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )
        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_submit_dates_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    @rollback
    async def test_answer_flow_items_create_for_respondent(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            created_at=1681216969,
            user_public_key="user key",
            answers=[
                dict(
                    flow_id="3013dfb1-9202-4577-80f2-ba7450fb5831",
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

    @rollback
    async def test_answer_with_skipping_all(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2",
            version="2.0.1",
            user_public_key="user key",
            created_at=1681216969,
            answers=[],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

    @rollback
    async def test_answered_applet_activities(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            user_public_key="user key",
            answers=[
                dict(
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.answered_applet_activities_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.date.today(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await self.client.get(
            self.activity_answers_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            )
        )

        assert response.status_code == 200, response.json()

        response = await self.client.get(
            self.activity_answers_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            )
        )

        assert response.status_code == 200, response.json()

    @pytest.mark.main
    @rollback
    async def test_assessment_applet_activities(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            user_public_key="user key",
            answers=[
                dict(
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.answered_applet_activities_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.date.today(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await self.client.get(
            self.assessment_answers_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            )
        )

        assert response.status_code == 200, response.json()

    @rollback
    async def test_applet_activities(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.answered_applet_activities_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.date.today(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 0

    @rollback
    async def test_add_note(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            user_public_key="user key",
            answers=[
                dict(
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.answered_applet_activities_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.date.today(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await self.client.post(
            self.answer_notes_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.answer_notes_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    @rollback
    async def test_edit_note(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            user_public_key="user key",
            answers=[
                dict(
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.answered_applet_activities_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.date.today(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await self.client.post(
            self.answer_notes_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.answer_notes_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note"

        response = await self.client.put(
            self.answer_note_detail_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
                note_id=response.json()["result"][0]["id"],
            ),
            dict(note="Some note 2"),
        )
        assert response.status_code == 200

        response = await self.client.get(
            self.answer_notes_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note 2"

    @rollback
    async def test_delete_note(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            user_public_key="user key",
            answers=[
                dict(
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
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
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.answered_applet_activities_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            dict(
                respondentId="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                createdDate=datetime.date.today(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await self.client.post(
            self.answer_notes_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.answer_notes_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note"

        response = await self.client.delete(
            self.answer_note_detail_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
                note_id=response.json()["result"][0]["id"],
            )
        )
        assert response.status_code == 204

        response = await self.client.get(
            self.answer_notes_url.format(
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
                answer_id=answer_id,
                activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 0

    @rollback
    async def test_answer_activity_items_create_for_not_respondent(self):
        await self.client.login(self.login_url, "patric@gmail.com", "Test1234")

        create_data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            version="1.0.0",
            user_public_key="user key",
            answers=[
                dict(
                    activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
                    answer=json.dumps(
                        dict(
                            value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                        )
                    ),
                    item_ids=[
                        "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                        "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
                    ],
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 403, response.json()
