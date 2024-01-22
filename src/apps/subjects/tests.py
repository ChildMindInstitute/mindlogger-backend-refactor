import http

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
    subject_respondent_url = "/subjects/respondents"

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
        res = await self.client.post(self.subject_respondent_url, body)
        assert res.status_code == http.HTTPStatus.OK
