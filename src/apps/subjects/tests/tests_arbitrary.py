import http
import json
import uuid

import pytest

from apps.answers.crud.answers import AnswersCRUD
from apps.shared.test import BaseTest
from apps.subjects.crud import SubjectsCrud


@pytest.fixture
def answer_create_payload():
    return dict(
        submit_id="270d86e0-2158-4d18-befd-86b3ce0122a1",
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


class TestSubjects(BaseTest):
    fixtures = ["answers/fixtures/arbitrary_server_answers.json"]

    login_url = "/auth/login"
    subject_list_url = "/subjects"
    subject_detail_url = "/subjects/{subject_id}"
    subject_respondent_url = "/subjects/{subject_id}/respondents"
    subject_respondent_details_url = "/subjects/{subject_id}/respondents/{respondent_id}"
    answer_url = "/answers"

    async def test_successfully_delete_subject_without_answers_arbitrary(
        self, session, arbitrary_session, arbitrary_client, answer_create_payload
    ):
        subject_id = uuid.UUID("a7feb119-dccb-46b1-bd46-60e5af694de4")
        await arbitrary_client.login(self.login_url, "ivan@mindlogger.com", "Test1234!")
        response = await arbitrary_client.post(self.answer_url, data=answer_create_payload)

        assert response.status_code == http.HTTPStatus.CREATED
        delete_url = self.subject_detail_url.format(subject_id=subject_id)
        res = await arbitrary_client.delete(delete_url, data=dict(deleteAnswers=False))
        assert res.status_code == http.HTTPStatus.OK

        subject = await SubjectsCrud(session).get_by_id(subject_id)
        assert subject, subject.is_deleted
        count = await AnswersCRUD(arbitrary_session).count(target_subject_id=subject_id)
        assert count

    async def test_successfully_delete_subject_with_answers_arbitrary(
        self, session, arbitrary_session, arbitrary_client, answer_create_payload, mock_kiq_report
    ):
        subject_id = uuid.UUID("a7feb119-dccb-46b1-bd46-60e5af694de4")
        await arbitrary_client.login(self.login_url, "ivan@mindlogger.com", "Test1234!")
        response = await arbitrary_client.post(self.answer_url, data=answer_create_payload)

        assert response.status_code == http.HTTPStatus.CREATED
        delete_url = self.subject_detail_url.format(subject_id=subject_id)
        res = await arbitrary_client.delete(delete_url, data=dict(deleteAnswers=True))
        assert res.status_code == http.HTTPStatus.OK
        subject = await SubjectsCrud(session).get_by_id(subject_id)
        assert not subject
        count = await AnswersCRUD(arbitrary_session).count(target_subject_id=subject_id)
        assert count == 0
