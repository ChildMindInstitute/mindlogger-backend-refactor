from apps.shared.test import BaseTest
from apps.subjects.domain import SubjectCreateRequest
from infrastructure.database import rollback


class TestSubjects(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
    ]

    login_url = "/auth/login"
    subject_list = "/subjects"

    @rollback
    async def test_create_subject(self):
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        relation = "father"
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = SubjectCreateRequest(
            applet_id=applet_id, relation=relation
        ).dict()
        response = await self.client.post(self.subject_list, data=create_data)
        assert response.status_code == 201
        payload = response.json()
        assert payload
        assert payload["result"]["appletId"] == applet_id
