import uuid

from apps.invitations.constants import InvitationStatus
from apps.invitations.crud import InvitationCRUD
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestInvite(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "invitations/fixtures/invitations.json",
    ]

    login_url = "/auth/login"
    invitation_list = "/invitations"
    invitation_detail = f"{invitation_list}/{{key}}"
    invite_url = f"{invitation_list}/invite"
    approve_url = f"{invitation_list}/approve/{{key}}"
    decline_url = f"{invitation_list}/decline/{{key}}"

    async def test_invitation_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.invitation_list)
        assert response.status_code == 200

        assert len(response.json()["result"]) == 2

    async def test_invitation_retrieve(self):
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
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

    @transaction.rollback
    async def test_invitation_approve(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.approve_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6")
        )
        assert response.status_code == 200
        invitation = await InvitationCRUD().get_by_email_and_key(
            "tom@mindlogger.com",
            uuid.UUID("6a3ab8e6-f2fa-49ae-b2db-197136677da6"),
        )
        assert invitation.status == InvitationStatus.APPROVED

    @transaction.rollback
    async def test_invitation_approve_wrong(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.approve_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da9")
        )
        assert response.status_code == 422

    @transaction.rollback
    async def test_invitation_decline(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.decline_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6")
        )
        assert response.status_code == 200
        invitation = await InvitationCRUD().get_by_email_and_key(
            "tom@mindlogger.com",
            uuid.UUID("6a3ab8e6-f2fa-49ae-b2db-197136677da6"),
        )
        assert invitation.status == InvitationStatus.DECLINED

    @transaction.rollback
    async def test_invitation_decline_wrong(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.decline_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da9")
        )
        assert response.status_code == 422
