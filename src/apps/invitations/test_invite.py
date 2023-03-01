import uuid

from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role
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
    private_invitation_detail = f"{invitation_list}/private/{{key}}"
    invite_url = f"{invitation_list}/invite"
    accept_url = f"{invitation_list}/{{key}}/accept"
    accept_private_url = f"{invitation_list}/private/{{key}}/accept"
    decline_url = f"{invitation_list}/{{key}}/decline"

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

        assert (
            response.json()["result"]["appletId"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b1"
        )
        assert response.json()["result"]["role"] == Role.MANAGER

    async def test_private_invitation_retrieve(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(
            self.private_invitation_detail.format(
                key="51857e10-6c05-4fa8-a2c8-725b8c1a0aa7"
            )
        )
        assert response.status_code == 200

        assert (
            response.json()["result"]["appletId"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b3"
        )
        assert response.json()["result"]["role"] == Role.RESPONDENT

    @transaction.rollback
    async def test_admin_invite_manager_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.REVIEWER,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.COORDINATOR,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.EDITOR,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.REVIEWER,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.RESPONDENT,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.MANAGER,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.COORDINATOR,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.EDITOR,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.REVIEWER,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.RESPONDENT,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.RESPONDENT,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.MANAGER,
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
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            role=Role.RESPONDENT,
        )
        response = await self.client.post(self.invite_url, request_data)
        assert response.status_code == 422
        assert (
            response.json()["result"][0]["message"]["en"]
            == "You do not have access to send invitation."
        )

    @transaction.rollback
    async def test_invitation_accept(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.accept_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6")
        )
        assert response.status_code == 200
        invitation = await InvitationCRUD().get_by_email_and_key(
            "tom@mindlogger.com",
            uuid.UUID("6a3ab8e6-f2fa-49ae-b2db-197136677da6"),
        )
        assert invitation.status == InvitationStatus.APPROVED

    @transaction.rollback
    async def test_private_invitation_accept(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.accept_private_url.format(
                key="51857e10-6c05-4fa8-a2c8-725b8c1a0aa7"
            )
        )
        assert response.status_code == 200
        access = await UserAppletAccessCRUD().get_by_roles(
            user_id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa1"),
            applet_id=uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b3"),
            roles=[Role.RESPONDENT],
        )
        assert access.role == Role.RESPONDENT

    @transaction.rollback
    async def test_invitation_accept_wrong(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.accept_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da9")
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
