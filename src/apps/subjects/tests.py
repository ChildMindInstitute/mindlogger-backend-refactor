import http
import uuid

import pytest

from apps.shared.test import BaseTest
from apps.subjects.domain import SubjectCreateRequest, SubjectRespondentCreate
from infrastructure.database import rollback, rollback_with_session


@pytest.fixture()
def create_shell_body():
    return SubjectCreateRequest(
        applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
        language="en",
        first_name="fn",
        last_name="ln",
        secret_user_id="1234",
    ).dict()


class TestSubjects(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
    ]

    login_url = "/auth/login"
    subject_list_url = "/subjects"
    subject_respondent_url = "/subjects/{subject_id}/respondents"
    subject_respondent_details_url = (
        "/subjects/{subject_id}/respondents/{respondent_id}"
    )

    @rollback_with_session
    async def test_create_subject(self, create_shell_body, **kwargs):
        creator_id = "7484f34a-3acc-4ee6-8a94-fd7299502fa1"
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.post(
            self.subject_list_url, data=create_shell_body
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload
        assert payload["result"]["appletId"] == applet_id
        assert payload["result"]["email"] is None
        assert payload["result"]["creatorId"] == creator_id
        assert payload["result"]["userId"] is None
        assert payload["result"]["language"] == "en"

    @rollback
    async def test_add_respondent(self, create_shell_body):
        creator_id = "7484f34a-3acc-4ee6-8a94-fd7299502fa1"
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.post(
            self.subject_list_url, data=create_shell_body
        )
        subject = response.json()
        body = SubjectRespondentCreate(
            user_id=creator_id,
            subject_id=subject["result"]["id"],
            applet_id=applet_id,
            relation="father",
        )
        url = self.subject_respondent_url.format(
            subject_id=subject["result"]["id"]
        )
        res = await self.client.post(url, body)
        assert res.status_code == http.HTTPStatus.OK

    @pytest.mark.parametrize(
        "subject_id,respondent_id,expected_code",
        (
            (uuid.uuid4(), None, http.HTTPStatus.NOT_FOUND),
            (None, uuid.uuid4(), http.HTTPStatus.NOT_FOUND),
            (None, None, http.HTTPStatus.OK),
        ),
    )
    @rollback
    async def test_remove_respondent(
        self, create_shell_body, subject_id, respondent_id, expected_code
    ):
        creator_id = "7484f34a-3acc-4ee6-8a94-fd7299502fa1"
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.post(
            self.subject_list_url, data=create_shell_body
        )
        subject = response.json()
        body = SubjectRespondentCreate(
            user_id=creator_id,
            subject_id=subject["result"]["id"],
            applet_id=applet_id,
            relation="father",
        )
        url = self.subject_respondent_url.format(
            subject_id=subject["result"]["id"]
        )
        respondent_res = await self.client.post(url, body)
        subject = respondent_res.json()
        subject_id_ = subject["result"]["id"]
        respondent_id_ = subject["result"]["subjects"][0]["userId"]
        url_delete = self.subject_respondent_details_url.format(
            subject_id=subject_id if subject_id else subject_id_,
            respondent_id=respondent_id if respondent_id else respondent_id_,
        )
        res = await self.client.delete(url_delete)
        assert res.status_code == expected_code
