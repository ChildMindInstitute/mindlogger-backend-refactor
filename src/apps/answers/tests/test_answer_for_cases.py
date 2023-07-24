import json

from apps.shared.test import BaseTest
from infrastructure.database import rollback


class TestAnswerCases(BaseTest):
    fixtures = ["answers/fixtures/duplicate_activity_in_flow.json"]

    login_url = "/auth/login"
    answer_url = "/answers"

    @rollback
    async def test_answer_activity_items_create_for_respondent(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            flow_id="3013dfb1-9202-4577-80f2-ba7450fb5831",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            version="1.0.0",
            created_at=1681216969,
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
                ],
                identifier="encrypted_identifier",
                scheduled_time=10,
                start_time=10,
                end_time=11,
            ),
        )

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        create_data = dict(
            submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            flow_id="3013dfb1-9202-4577-80f2-ba7450fb5831",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3621",
            version="1.0.0",
            created_at=1681216969,
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
                    "a18d3409-2c96-4a5e-a1f3-1c1c14be0021",
                ],
                identifier="encrypted_identifier",
                scheduled_time=10,
                start_time=10,
                end_time=11,
            ),
        )

        response = await self.client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
