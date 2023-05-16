import uuid

from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from infrastructure.database import rollback


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
    invitation_detail = "/invitations/{key}"
    private_invitation_detail = "/invitations/private/{key}"
    invite_url = "/invitations/invite"
    accept_url = "/invitations/{key}/accept"
    accept_private_url = "/invitations/private/{key}/accept"
    decline_url = "/invitations/{key}/decline"
    invite_manager_url = f"{invitation_list}/{{applet_id}}/managers"
    invite_reviewer_url = f"{invitation_list}/{{applet_id}}/reviewer"
    invite_respondent_url = f"{invitation_list}/{{applet_id}}/respondent"

    @rollback
    async def test_invitation_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.invitation_list)
        assert response.status_code == 200

        assert len(response.json()["result"]) == 2

    @rollback
    async def test_applets_invitation_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.invitation_list,
            dict(appletId="92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )
        assert response.status_code == 200

        assert len(response.json()["result"]) == 1

    @rollback
    async def test_invitation_retrieve(self):
        await self.client.login(self.login_url, "mike@gmail.com", "Test1234")

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

    @rollback
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

    @rollback
    async def test_admin_invite_manager_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.MANAGER,
            language="en",
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        assert TestMail.mails[0].subject == "Applet 1 invitation"

    @rollback
    async def test_admin_invite_coordinator_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.COORDINATOR,
            language="en",
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

    @rollback
    async def test_admin_invite_editor_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.EDITOR,
            language="en",
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

    @rollback
    async def test_admin_invite_reviewer_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.REVIEWER,
            language="en",
            respondents=["7484f34a-3acc-4ee6-8a94-fd7299502fa1"],
        )
        response = await self.client.post(
            self.invite_reviewer_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200, response.json()

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        assert TestMail.mails[0].subject == "Applet 1 invitation"

    @rollback
    async def test_admin_invite_respondent_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.RESPONDENT,
            language="en",
            secret_user_id=str(uuid.uuid4()),
            nickname=str(uuid.uuid4()),
        )
        response = await self.client.post(
            self.invite_respondent_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        assert TestMail.mails[0].subject == "Applet 1 invitation"

    @rollback
    async def test_admin_invite_respondent_duplicate_pending_secret_id(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.RESPONDENT,
            language="en",
            secret_user_id=str(uuid.uuid4()),
            nickname=str(uuid.uuid4()),
        )
        response = await self.client.post(
            self.invite_respondent_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        request_data["email"] = "patric1@gmail.com"
        response = await self.client.post(
            self.invite_respondent_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 422

    @rollback
    async def test_manager_invite_manager_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.MANAGER,
            language="en",
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]
        assert TestMail.mails[0].subject == "Applet 1 invitation"

    @rollback
    async def test_manager_invite_coordinator_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.COORDINATOR,
            language="en",
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

    @rollback
    async def test_manager_invite_editor_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.EDITOR,
            language="en",
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

    @rollback
    async def test_manager_invite_reviewer_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.REVIEWER,
            language="en",
            respondents=["7484f34a-3acc-4ee6-8a94-fd7299502fa1"],
        )
        response = await self.client.post(
            self.invite_reviewer_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

    @rollback
    async def test_manager_invite_respondent_success(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.RESPONDENT,
            language="en",
            secret_user_id=str(uuid.uuid4()),
            nickname=str(uuid.uuid4()),
        )
        response = await self.client.post(
            self.invite_respondent_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

    @rollback
    async def test_coordinator_invite_respondent_success(self):
        await self.client.login(self.login_url, "bob@gmail.com", "Test1234!")
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.RESPONDENT,
            language="en",
            secret_user_id=str(uuid.uuid4()),
            nickname=str(uuid.uuid4()),
        )
        response = await self.client.post(
            self.invite_respondent_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

    @rollback
    async def test_coordinator_invite_reviewer_success(self):
        await self.client.login(self.login_url, "bob@gmail.com", "Test1234!")
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.REVIEWER,
            language="en",
            respondents=["7484f34a-3acc-4ee6-8a94-fd7299502fa1"],
        )
        response = await self.client.post(
            self.invite_reviewer_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

    @rollback
    async def test_coordinator_invite_manager_fail(self):
        await self.client.login(self.login_url, "bob@gmail.com", "Test1234!")
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.MANAGER,
            language="en",
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )

        assert response.status_code == 400
        assert response.json()["result"][0]["message"] == "Access denied."

    @rollback
    async def test_editor_invite_respondent_fail(self):
        await self.client.login(self.login_url, "mike2@gmail.com", "Test1234")
        request_data = dict(
            email="patric@gmail.com",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            first_name="Patric",
            last_name="Daniel",
            language="en",
            role=Role.RESPONDENT,
            secret_user_id=str(uuid.uuid4()),
            nickname=str(uuid.uuid4()),
        )
        response = await self.client.post(
            self.invite_respondent_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 403
        assert (
            response.json()["result"][0]["message"]
            == "Access denied to manipulate with invites of the applet."
        )

    @rollback
    async def test_invitation_accept_and_absorb_roles(self):
        await self.client.login(self.login_url, "mike@gmail.com", "Test1234")

        roles = await UserAppletAccessCRUD().get_user_roles_to_applet(
            uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa4"),
            uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )
        assert len(roles) == 2
        assert roles[0] == Role.COORDINATOR
        assert roles[1] == Role.EDITOR

        response = await self.client.post(
            self.accept_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6")
        )
        assert response.status_code == 200
        roles = await UserAppletAccessCRUD().get_user_roles_to_applet(
            uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa4"),
            uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )
        assert len(roles) == 2
        assert roles[0] == Role.MANAGER
        assert roles[1] == Role.RESPONDENT

    @rollback
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
            ordered_roles=[Role.RESPONDENT],
        )
        assert access.role == Role.RESPONDENT

    @rollback
    async def test_invitation_accept_wrong(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.accept_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da9")
        )
        assert response.status_code == 404

    @rollback
    async def test_invitation_decline(self):
        await self.client.login(self.login_url, "mike@gmail.com", "Test1234")

        response = await self.client.delete(
            self.decline_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6")
        )
        assert response.status_code == 200

    @rollback
    async def test_invitation_decline_wrong(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.decline_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da9")
        )
        assert response.status_code == 404
