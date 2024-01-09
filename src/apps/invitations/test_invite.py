import json
import uuid

import pytest

from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role
from apps.invitations.crud import InvitationCRUD
from apps.invitations.domain import InvitationStatus
from apps.invitations.errors import (
    ManagerInvitationExist,
    RespondentInvitationExist,
)
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.users.domain import UserCreateRequest
from infrastructure.database import rollback, session_manager


@pytest.fixture
def user_create_data() -> UserCreateRequest:
    return UserCreateRequest(
        email="tom2@mindlogger.com",
        first_name="Tom",
        last_name="Isaak",
        password="Test1234!",
    )


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

        assert len(response.json()["result"]) == 4

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

        assert len(response.json()["result"]) == 3

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
        assert (
            response.json()["result"]["userId"]
            == "7484f34a-3acc-4ee6-8a94-fd7299502fa5"
        )
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
        assert (
            response.json()["result"]["userId"]
            == "7484f34a-3acc-4ee6-8a94-fd7299502fa5"
        )
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
        assert (
            response.json()["result"]["userId"]
            == "7484f34a-3acc-4ee6-8a94-fd7299502fa5"
        )
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
        assert (
            response.json()["result"]["userId"]
            == "7484f34a-3acc-4ee6-8a94-fd7299502fa5"
        )
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
        assert (
            response.json()["result"]["userId"]
            == "7484f34a-3acc-4ee6-8a94-fd7299502fa5"
        )
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

        assert response.status_code == 403
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

        roles = await UserAppletAccessCRUD(
            session_manager.get_session()
        ).get_user_roles_to_applet(
            uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa4"),
            uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )
        assert len(roles) == 3
        assert Role.COORDINATOR in roles
        assert Role.EDITOR in roles

        response = await self.client.post(
            self.accept_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6")
        )
        assert response.status_code == 200
        roles = await UserAppletAccessCRUD(
            session_manager.get_session()
        ).get_user_roles_to_applet(
            uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa4"),
            uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )
        assert len(roles) == 2
        assert Role.MANAGER in roles
        assert Role.RESPONDENT in roles

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
        access = await UserAppletAccessCRUD(
            session_manager.get_session()
        ).get_by_roles(
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
            self.decline_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da0")
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

    @rollback
    @pytest.mark.parametrize(
        "role", (Role.MANAGER, Role.COORDINATOR, Role.EDITOR)
    )
    async def test_manager_invite_if_duplicate_email_and_role_not_accepted(
        self, role
    ):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        request_data = dict(
            email="person@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=role,
            language="en",
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200

        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200
        assert len(TestMail.mails) == 2

    @rollback
    async def test_admin_invite_respondent_fail_if_duplicate_email(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="mike@gmail.com",
            first_name="Mike",
            last_name="M",
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
        assert response.status_code == 422
        res = json.loads(response.content)
        res = res["result"][0]
        assert res["message"] == RespondentInvitationExist.message
        assert len(TestMail.mails) == 0

    @rollback
    async def test_fail_if_invite_manager_on_editor_role(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="mike@gmail.com",
            first_name="Mike",
            last_name="M",
            role=Role.EDITOR,
            language="en",
            secret_user_id=str(uuid.uuid4()),
            nickname=str(uuid.uuid4()),
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2"
            ),
            request_data,
        )
        assert response.status_code == 422
        res = json.loads(response.content)
        res = res["result"][0]
        assert res["message"] == ManagerInvitationExist.message
        assert len(TestMail.mails) == 0

    @rollback
    async def test_invite_not_registered_user_manager(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patricnewuser@example.com",
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
        assert not response.json()["result"]["userId"]
        assert len(TestMail.mails) == 1

    @rollback
    async def test_invite_not_registered_user_reviewer(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patricnewuser@example.com",
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
        assert not response.json()["result"]["userId"]
        assert len(TestMail.mails) == 1

    @rollback
    async def test_invite_not_registered_user_respondent(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patricnewuser@example.com",
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
        assert not response.json()["result"]["userId"]
        assert len(TestMail.mails) == 1

    @rollback
    @pytest.mark.parametrize(
        "status,url,method",
        (
            (InvitationStatus.APPROVED, "accept_url", "post"),
            (InvitationStatus.DECLINED, "decline_url", "delete"),
        ),
    )
    async def test_new_user_accept_decline_invitation(
        self, user_create_data, status, url, method
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patricnewuser@example.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.MANAGER,
            language="en",
        )
        email = request_data["email"]
        # Send an invite
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200
        assert not response.json()["result"]["userId"]

        invitation_key = response.json()["result"]["key"]
        user_create_data.email = email
        data = user_create_data.dict()
        # An invited user creates an account
        resp = await self.client.post("/users", data=data)
        assert resp.status_code == 201
        resp = await self.client.login(self.login_url, email, data["password"])
        exp_user_id = resp.json()["result"]["user"]["id"]
        # Accept invite
        client_method = getattr(self.client, method)
        resp = await client_method(
            getattr(self, url).format(key=invitation_key)
        )
        assert resp.status_code == 200
        session = session_manager.get_session()
        # Because we don't return anything after accepting/declining
        # invitation, check in database that user_id has already been updated
        inv = await InvitationCRUD(session).get_by_email_and_key(
            email, uuid.UUID(invitation_key)
        )
        assert str(inv.user_id) == exp_user_id  # type: ignore[union-attr]
        assert inv.status == status  # type: ignore[union-attr]

    @rollback
    async def test_update_invitation_for_new_user_who_registered_after_first_invitation(  # noqa: E501
        self, user_create_data
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patricnewuser@example.com",
            first_name="Patric",
            last_name="DanielUpdated",
            role=Role.MANAGER,
            language="en",
        )
        email = request_data["email"]
        # Send an invite
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200
        assert not response.json()["result"]["userId"]

        user_create_data.email = email
        data = user_create_data.dict()
        # An invited user creates an account
        resp = await self.client.post("/users", data=data)
        assert resp.status_code == 201
        resp = await self.client.login(self.login_url, email, data["password"])
        exp_user_id = resp.json()["result"]["user"]["id"]

        # Update an invite
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200
        assert response.json()["result"]["userId"] == exp_user_id

    @rollback
    async def test_resend_invitation_with_updates_for_respondent_with_pending_invitation(  # noqa: E501
        self,
    ):
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

        # change first name and last name for user for tests
        # update secret_user_id because it should be unique
        request_data["first_name"] = "test"
        request_data["last_name"] = "test"

        response = await self.client.post(
            self.invite_respondent_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200
        invitation_key = response.json()["result"]["key"]
        session = session_manager.get_session()
        # Because we don't return anything after accepting/declining
        # invitation, check in database that user_id has already been updated
        inv = await InvitationCRUD(session).get_by_email_and_key(
            request_data["email"], uuid.UUID(invitation_key)
        )
        assert inv.first_name == request_data["first_name"]
        assert inv.last_name == request_data["last_name"]

    @rollback
    async def test_resend_invitation_for_respondent_with_pending_invitation_only_last_key_valid(  # noqa: E501
        self,
    ):
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
        old_key = response.json()["result"]["key"]

        response = await self.client.post(
            self.invite_respondent_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            request_data,
        )
        assert response.status_code == 200
        new_key = response.json()["result"]["key"]
        await self.client.login(self.login_url, "patric@gmail.com", "Test1234")

        response = await self.client.get(
            self.invitation_detail.format(key=old_key)
        )
        assert response.status_code == 404

        # we use invitation detail url for tests, because sninny atomic
        # does not work correct in tests.
        response = await self.client.get(
            self.invitation_detail.format(key=new_key)
        )
        assert response.status_code == 200
