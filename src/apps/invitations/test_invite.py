from apps.mailing.services import TestMail
from apps.shared.test import BaseTest


class TestInvite(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
    ]

    login_url = "/auth/login"
    invite_url = "/invitations/invite"
    approve_url = "/invitations/approve/{key}"

    async def test_admin_invite_manager_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="reviewer",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_admin_invite_coordinator_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="coordinator",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_admin_invite_editor_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="editor",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_admin_invite_reviewer_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="reviewer",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_admin_invite_respondent_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="respondent",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_manager_invite_manager_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="manager",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_manager_invite_coordinator_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="coordinator",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_manager_invite_editor_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="editor",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_manager_invite_reviewer_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="reviewer",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_manager_invite_respondent_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="respondent",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_coordinator_invite_respondent_success(self):
        await self.client.login(self.login_url, "bob@gmail.com", "Test1234!")
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="respondent",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        TestMail.clear_mails()

    async def test_coordinator_invite_manager_fail(self):
        await self.client.login(self.login_url, "bob@gmail.com", "Test1234!")
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="manager",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 422
        assert (
            response.json()["result"][0]["message"]["en"]
            == "You do not have access to send invitation."
        )

    async def test_editor_invite_any_fail(self):
        await self.client.login(self.login_url, "mike@gmail.com", "Test1234")
        request_data = dict(
            email="patric@gmail.com",
            applet_id=1,
            role="respondent",
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 422
        assert (
            response.json()["result"][0]["message"]["en"]
            == "You do not have access to send invitation."
        )
