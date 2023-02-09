import datetime
import json

import pytest

from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from infrastructure.utility import RedisCache


@pytest.fixture
async def create_cache_invitations():
    cache = RedisCache()
    invitations = {
        "InvitationsCache:tom@mindlogger.com:"
        "6a3ab8e6-f2fa-49ae-b2db-197136677da6": dict(
            instance=dict(
                email="tom@mindlogger.com",
                applet_id=1,
                role="manager",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da6",
                invitor_id=1,
            ),
            created_at=datetime.datetime.now().isoformat(),
        ),
        "InvitationsCache:tom@mindlogger.com:"
        "6a3ab8e6-f2fa-49ae-b2db-197136677da7": dict(
            instance=dict(
                email="tom@mindlogger.com",
                applet_id=1,
                role="reviewer",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
                invitor_id=1,
            ),
            created_at=datetime.datetime.now().isoformat(),
        ),
    }
    for key, value in invitations.items():
        await cache.set(key, json.dumps(value))


class TestInvite(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
    ]

    login_url = "/auth/login"
    invitation_list = "/invitations"
    invitation_detail = f"{invitation_list}/{{key}}"
    invite_url = f"{invitation_list}/invite"
    approve_url = f"{invitation_list}/approve/{{key}}"

    async def test_invitation_list(self, create_cache_invitations):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.invitation_list)
        assert response.status_code == 200

        assert len(response.json()["result"]) == 2

    async def test_invitation_retrieve(self, create_cache_invitations):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.invitation_detail.format(
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da6"
            )
        )
        assert response.status_code == 200

        assert response.json()["result"]["appletId"] == 1
        assert response.json()["result"]["role"] == "manager"

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
