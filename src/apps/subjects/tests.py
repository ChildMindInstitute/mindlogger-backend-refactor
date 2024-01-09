from apps.shared.test import BaseTest
from apps.subjects.domain import SubjectCreateRequest
from infrastructure.database import rollback_with_session


class TestSubjects(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
    ]

    login_url = "/auth/login"
    subject_list = "/subjects"

    @rollback_with_session
    async def test_create_subject(self, **kwargs):
        lang = "en"
        creator_id = "7484f34a-3acc-4ee6-8a94-fd7299502fa1"
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = SubjectCreateRequest(
            applet_id=applet_id,
            language=lang,
            first_name="fn",
            last_name="ln",
            secret_user_id="1234",
        ).dict()
        response = await self.client.post(self.subject_list, data=create_data)
        assert response.status_code == 201
        payload = response.json()
        assert payload
        assert payload["result"]["appletId"] == applet_id
        assert payload["result"]["email"] is None
        assert payload["result"]["creatorId"] == creator_id
        assert payload["result"]["userId"] is None
        assert payload["result"]["language"] == "en"
