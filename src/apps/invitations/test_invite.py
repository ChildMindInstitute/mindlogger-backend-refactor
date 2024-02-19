import http
import json
import uuid
from typing import Literal

import pytest
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import ManagersRole, Role
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.service.applet import AppletService
from apps.invitations.crud import InvitationCRUD
from apps.invitations.domain import (
    InvitationManagersRequest,
    InvitationRespondentRequest,
    InvitationReviewerRequest,
    InvitationStatus,
)
from apps.invitations.errors import (
    InvitationAlreadyProcessed,
    InvitationDoesNotExist,
    ManagerInvitationExist,
    NonUniqueValue,
    RespondentDoesNotExist,
    RespondentInvitationExist,
)
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.users.domain import UserCreate, UserCreateRequest
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture
async def applet_one_with_public_link(session: AsyncSession, applet_one: AppletFull, tom):
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet_one.id, CreateAccessLink(require_login=False))
    applet = await srv.get_full_applet(applet_one.id)
    assert applet.link is not None
    return applet


@pytest.fixture
async def applet_one_with_link(session: AsyncSession, applet_one: AppletFull, tom):
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet_one.id, CreateAccessLink(require_login=True))
    applet = await srv.get_full_applet(applet_one.id)
    assert applet.link is not None
    return applet


@pytest.fixture
async def applet_one_lucy_manager(session: AsyncSession, applet_one: AppletFull, tom, lucy) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.MANAGER)
    return applet_one


@pytest.fixture
async def applet_one_lucy_coordinator(session: AsyncSession, applet_one: AppletFull, tom, lucy) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.COORDINATOR)
    return applet_one


@pytest.fixture
async def applet_one_lucy_editor(session: AsyncSession, applet_one: AppletFull, tom, lucy) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.EDITOR)
    return applet_one


@pytest.fixture
async def applet_one_lucy_respondent(session: AsyncSession, applet_one: AppletFull, tom, lucy) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.RESPONDENT)
    return applet_one


@pytest.fixture
async def applet_one_lucy_roles(
    applet_one_lucy_respondent: AppletFull, applet_one_lucy_coordinator: AppletFull, applet_one_lucy_editor: AppletFull
) -> list[AppletFull]:
    return [applet_one_lucy_respondent, applet_one_lucy_coordinator, applet_one_lucy_editor]


@pytest.fixture
def user_create_data() -> UserCreateRequest:
    return UserCreateRequest(
        email=EmailStr("tom2@mindlogger.com"),
        first_name="Tom",
        last_name="Isaak",
        password="Test1234!",
    )


@pytest.fixture
def respondent_ids(tom) -> list[str]:
    return [tom.id]


@pytest.fixture
def invitation_base_data(user_create: UserCreate) -> dict[str, str | EmailStr]:
    return dict(
        email=user_create.email,
        first_name=user_create.first_name,
        last_name=user_create.last_name,
        language="en",
    )


@pytest.fixture
def invitation_manager_data(invitation_base_data: dict[str, str | EmailStr]) -> InvitationManagersRequest:
    return InvitationManagersRequest(**invitation_base_data, role=ManagersRole.MANAGER)


@pytest.fixture
def invitation_editor_data(invitation_base_data: dict[str, str | EmailStr]) -> InvitationManagersRequest:
    return InvitationManagersRequest(**invitation_base_data, role=ManagersRole.EDITOR)


@pytest.fixture
def invitation_coordinator_data(
    invitation_base_data: dict[str, str | EmailStr],
) -> InvitationManagersRequest:
    return InvitationManagersRequest(**invitation_base_data, role=ManagersRole.COORDINATOR)


@pytest.fixture
def invitation_respondent_data(
    invitation_base_data: dict[str, str | EmailStr],
) -> InvitationRespondentRequest:
    return InvitationRespondentRequest(
        **invitation_base_data,
        secret_user_id=str(uuid.uuid4()),
        nickname=str(uuid.uuid4()),
    )


@pytest.fixture
def invitation_revier_data(
    invitation_base_data: dict[str, str | EmailStr], respondent_ids
) -> InvitationReviewerRequest:
    return InvitationReviewerRequest(**invitation_base_data, respondents=respondent_ids)


class TestInvite(BaseTest):
    fixtures = [
        "invitations/fixtures/invitations.json",
    ]

    login_url = "/auth/login"
    invitation_list = "/invitations"
    invitation_detail = "/invitations/{key}"
    private_invitation_detail = "/invitations/private/{key}"
    invite_url = "/invitations/invite"
    invited_url = "/invitations/invited"
    accept_url = "/invitations/{key}/accept"
    accept_private_url = "/invitations/private/{key}/accept"
    decline_url = "/invitations/{key}/decline"
    invite_manager_url = f"{invitation_list}/{{applet_id}}/managers"
    invite_reviewer_url = f"{invitation_list}/{{applet_id}}/reviewer"
    invite_respondent_url = f"{invitation_list}/{{applet_id}}/respondent"

    async def test_invitation_list(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(self.invitation_list)
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.json()["result"]) == 2

    async def test_applets_invitation_list(self, client, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(
            self.invitation_list,
            dict(appletId=str(applet_one.id)),
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.json()["result"]) == 1

    async def test_invitation_retrieve(self, client, applet_one):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.get(self.invitation_detail.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6"))
        assert response.status_code == http.HTTPStatus.OK

        assert response.json()["result"]["appletId"] == str(applet_one.id)
        assert response.json()["result"]["role"] == Role.MANAGER

    async def test_private_invitation_retrieve(self, client, applet_one_with_link):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.get(self.private_invitation_detail.format(key=applet_one_with_link.link))
        assert response.status_code == http.HTTPStatus.OK

        assert response.json()["result"]["appletId"] == str(applet_one_with_link.id)
        assert response.json()["result"]["role"] == Role.RESPONDENT

    async def test_admin_invite_manager_success(self, client, invitation_manager_data, tom, user, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["userId"] == str(user.id)
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_manager_data.email]
        assert TestMail.mails[0].subject == "Applet 1 invitation"

    async def test_admin_invite_coordinator_success(self, client, invitation_coordinator_data, tom, user, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_coordinator_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["userId"] == str(user.id)
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_coordinator_data.email]

    async def test_admin_invite_editor_success(self, client, invitation_editor_data, tom, user, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_editor_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["userId"] == str(user.id)
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_editor_data.email]

    async def test_admin_invite_reviewer_success(self, client, invitation_revier_data, tom, user, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_revier_data,
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["userId"] == str(user.id)
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_revier_data.email]
        assert TestMail.mails[0].subject == "Applet 1 invitation"

    async def test_admin_invite_respondent_success(self, client, invitation_respondent_data, tom, user, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["userId"] == str(user.id)
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_respondent_data.email]
        assert TestMail.mails[0].subject == "Applet 1 invitation"

    async def test_admin_invite_respondent_duplicate_pending_secret_id(
        self, client, invitation_respondent_data, tom, applet_one
    ):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        invitation_respondent_data.email = "patric1@gmail.com"
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["result"][0]["message"] == NonUniqueValue.message

    async def test_manager_invite_manager_success(self, client, invitation_manager_data, applet_one_lucy_manager):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one_lucy_manager.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_manager_data.email]
        assert TestMail.mails[0].subject == "Applet 1 invitation"

    async def test_manager_invite_coordinator_success(
        self, client, invitation_coordinator_data, applet_one_lucy_manager
    ):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one_lucy_manager.id)),
            invitation_coordinator_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_coordinator_data.email]

    async def test_manager_invite_editor_success(self, client, invitation_editor_data, applet_one_lucy_manager):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one_lucy_manager.id)),
            invitation_editor_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_editor_data.email]

    async def test_manager_invite_reviewer_success(self, client, invitation_revier_data, applet_one_lucy_manager):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one_lucy_manager.id)),
            invitation_revier_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_revier_data.email]

    async def test_manager_invite_respondent_success(self, client, invitation_respondent_data, applet_one_lucy_manager):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one_lucy_manager.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_respondent_data.email]

    async def test_coordinator_invite_respondent_success(
        self, client, invitation_respondent_data, applet_one_lucy_coordinator
    ):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one_lucy_coordinator.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_respondent_data.email]

    async def test_coordinator_invite_reviewer_success(
        self, client, invitation_revier_data, applet_one_lucy_coordinator
    ):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one_lucy_coordinator.id)),
            invitation_revier_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [invitation_revier_data.email]

    async def test_coordinator_invite_manager_fail(self, client, invitation_manager_data, applet_one_lucy_coordinator):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one_lucy_coordinator.id)),
            invitation_manager_data,
        )

        assert response.status_code == 403
        assert response.json()["result"][0]["message"] == "Access denied."

    async def test_editor_invite_respondent_fail(
        self, client, invitation_respondent_data, lucy, applet_one_lucy_editor
    ):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one_lucy_editor.id)),
            invitation_respondent_data,
        )
        assert response.status_code == 403
        assert response.json()["result"][0]["message"] == "Access denied to manipulate with invites of the applet."

    async def test_invitation_accept_and_absorb_roles(self, session, client, lucy, applet_one_lucy_roles, applet_one):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        roles = await UserAppletAccessCRUD(session).get_user_roles_to_applet(lucy.id, applet_one.id)
        assert len(roles) == 3
        assert Role.COORDINATOR in roles
        assert Role.EDITOR in roles
        assert Role.RESPONDENT in roles

        response = await client.post(self.accept_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6"))
        assert response.status_code == http.HTTPStatus.OK
        roles = await UserAppletAccessCRUD(session).get_user_roles_to_applet(lucy.id, applet_one.id)
        assert len(roles) == 2
        assert Role.MANAGER in roles
        assert Role.RESPONDENT in roles

    async def test_private_invitation_accept(self, session, client, lucy, applet_one_with_link):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

        response = await client.post(self.accept_private_url.format(key=applet_one_with_link.link))
        assert response.status_code == http.HTTPStatus.OK
        access = await UserAppletAccessCRUD(session).get_by_roles(
            user_id=lucy.id,
            applet_id=applet_one_with_link.id,
            ordered_roles=[Role.RESPONDENT],
        )
        assert access.role == Role.RESPONDENT

    async def test_invitation_accept_invitation_does_not_exists(self, client, tom, uuid_zero):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.post(self.accept_url.format(key=uuid_zero))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_invitation_decline(self, client, lucy):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

        response = await client.delete(self.decline_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6"))
        assert response.status_code == http.HTTPStatus.OK

    async def test_invitation_decline_wrong_invitation_does_not_exists(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.delete(self.decline_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da9"))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        assert response.json()["result"][0]["message"] == InvitationDoesNotExist.message

    @pytest.mark.parametrize("role", (Role.MANAGER, Role.COORDINATOR, Role.EDITOR))
    async def test_manager_invite_if_duplicate_email_and_role_not_accepted(
        self, client, role, invitation_manager_data, applet_one_lucy_manager
    ):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        invitation_manager_data.role = role
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one_lucy_manager.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one_lucy_manager.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(TestMail.mails) == 2

    async def test_admin_invite_respondent_fail_if_duplicate_email(
        self, client, invitation_respondent_data, tom, applet_one_lucy_respondent, lucy
    ):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        invitation_respondent_data.email = lucy.email_encrypted
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one_lucy_respondent.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        res = json.loads(response.content)
        res = res["result"][0]
        assert res["message"] == RespondentInvitationExist.message
        assert len(TestMail.mails) == 0

    async def test_fail_if_invite_manager_on_editor_role(
        self, client, invitation_editor_data, tom, applet_one_lucy_manager, lucy
    ):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        invitation_editor_data.email = lucy.email_encrypted
        response = await client.post(
            self.invite_manager_url.format(applet_id=applet_one_lucy_manager.id),
            invitation_editor_data,
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        res = json.loads(response.content)
        res = res["result"][0]
        assert res["message"] == ManagerInvitationExist.message
        assert len(TestMail.mails) == 0

    async def test_invite_not_registered_user_manager(self, client, invitation_manager_data, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        invitation_manager_data.email = f"new{invitation_manager_data.email}"
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert not response.json()["result"]["userId"]
        assert len(TestMail.mails) == 1

    async def test_invite_not_registered_user_reviewer(self, client, invitation_revier_data, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        invitation_revier_data.email = f"new{invitation_revier_data.email}"
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_revier_data,
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert not response.json()["result"]["userId"]
        assert len(TestMail.mails) == 1

    async def test_invite_not_registered_user_respondent(self, client, invitation_respondent_data, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        invitation_respondent_data.email = f"new{invitation_respondent_data.email}"
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert not response.json()["result"]["userId"]
        assert len(TestMail.mails) == 1

    @pytest.mark.parametrize(
        "status,url,method",
        (
            (InvitationStatus.APPROVED, "accept_url", "post"),
            (InvitationStatus.DECLINED, "decline_url", "delete"),
        ),
    )
    async def test_new_user_accept_decline_invitation(
        self, session, client, user_create_data, status, url, method, invitation_manager_data, tom, applet_one
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        new_email = f"new{invitation_manager_data.email}"
        invitation_manager_data.email = new_email
        # Send an invite
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert not response.json()["result"]["userId"]

        invitation_key = response.json()["result"]["key"]
        user_create_data.email = new_email
        # An invited user creates an account
        resp = await client.post("/users", data=user_create_data)
        assert resp.status_code == http.HTTPStatus.CREATED
        resp = await client.login(self.login_url, new_email, user_create_data.password)
        exp_user_id = resp.json()["result"]["user"]["id"]
        # Accept invite
        client_method = getattr(client, method)
        resp = await client_method(getattr(self, url).format(key=invitation_key))
        assert resp.status_code == http.HTTPStatus.OK
        # Because we don't return anything after accepting/declining
        # invitation, check in database that user_id has already been updated
        inv = await InvitationCRUD(session).get_by_email_and_key(new_email, uuid.UUID(invitation_key))
        assert str(inv.user_id) == exp_user_id  # type: ignore[union-attr]
        assert inv.status == status  # type: ignore[union-attr]

    async def test_update_invitation_for_new_user_who_registered_after_first_invitation(
        self, client, user_create_data, invitation_manager_data, tom, applet_one
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        new_email = f"new{invitation_manager_data.email}"
        invitation_manager_data.email = new_email
        # Send an invite
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert not response.json()["result"]["userId"]

        user_create_data.email = new_email
        # An invited user creates an account
        resp = await client.post("/users", data=user_create_data)
        assert resp.status_code == http.HTTPStatus.CREATED
        resp = await client.login(self.login_url, new_email, user_create_data.password)
        exp_user_id = resp.json()["result"]["user"]["id"]

        # Update an invite
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["userId"] == exp_user_id

    async def test_resend_invitation_with_updates_for_respondent_with_pending_invitation(
        self, session, client, invitation_respondent_data, tom, applet_one
    ):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        # change first name and last name for user for tests
        # update secret_user_id because it should be unique
        invitation_respondent_data.first_name = "test"
        invitation_respondent_data.last_name = "test"

        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        invitation_key = response.json()["result"]["key"]
        # Because we don't return anything after accepting/declining
        # invitation, check in database that user_id has already been updated
        inv = await InvitationCRUD(session).get_by_email_and_key(
            invitation_respondent_data.email, uuid.UUID(invitation_key)
        )
        assert inv.first_name == invitation_respondent_data.first_name
        assert inv.last_name == invitation_respondent_data.last_name

    async def test_resend_invitation_for_respondent_with_pending_invitation_only_last_key_valid(
        self, client, invitation_respondent_data, tom, applet_one
    ):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        old_key = response.json()["result"]["key"]

        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        new_key = response.json()["result"]["key"]
        await client.login(self.login_url, invitation_respondent_data.email, "Test1234!")

        response = await client.get(self.invitation_detail.format(key=old_key))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

        # we use invitation detail url for tests, because sninny atomic
        # does not work correct in tests.
        response = await client.get(self.invitation_detail.format(key=new_key))
        assert response.status_code == http.HTTPStatus.OK

    async def test_send_many_pending_invitations_for_one_email_valid_only_last(
        self,
        client,
        session,
        invitation_coordinator_data,
        invitation_editor_data,
        invitation_manager_data,
        invitation_respondent_data,
        invitation_revier_data,
        tom,
        applet_one,
    ):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        invitations_urls = [
            (invitation_coordinator_data, self.invite_manager_url),
            (invitation_editor_data, self.invite_manager_url),
            (invitation_manager_data, self.invite_manager_url),
            (invitation_respondent_data, self.invite_respondent_url),
            (invitation_revier_data, self.invite_reviewer_url),
        ]
        applet_id = str(applet_one.id)
        keys = []
        for invite, url in invitations_urls:
            resp = await client.post(
                url.format(applet_id=applet_id),
                data=invite,
            )
            assert resp.status_code == http.HTTPStatus.OK
            keys.append(resp.json()["result"]["key"])
        last_invitation = invitations_urls[-1][0]
        count_invitations = await InvitationCRUD(session).count(
            email=last_invitation.email,
            applet_id=uuid.UUID(applet_id),
            status=InvitationStatus.PENDING,
        )
        # Only one invite
        assert count_invitations == 1

        await client.login(self.login_url, invitation_respondent_data.email, "Test1234!")
        # Check first and last invitations to test that only last is valid
        response = await client.get(self.invitation_detail.format(key=keys[0]))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        response = await client.get(self.invitation_detail.format(key=keys[-1]))
        assert response.status_code == http.HTTPStatus.OK

    async def test_get_invitation_by_key_invitation_does_not_exist(self, client, tom, uuid_zero):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(self.invitation_detail.format(key=uuid_zero))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        assert response.json()["result"][0]["message"] == InvitationDoesNotExist.message

    @pytest.mark.parametrize(
        "url,method",
        (("decline_url", "delete"), ("accept_url", "post")),
    )
    async def test_get_invitation_by_key_already_accpted_declined(
        self, client, url: Literal["decline_url", "accept_url"], method: Literal["delete", "post"], lucy
    ):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")
        key = "6a3ab8e6-f2fa-49ae-b2db-197136677da6"
        client_method = getattr(client, method)
        url_ = getattr(self, url)
        response = await client_method(url_.format(key=key))
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(self.invitation_detail.format(key=key))
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == InvitationAlreadyProcessed.message

    async def test_get_private_invitation_by_link_does_not_exist(self, client, tom, uuid_zero):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(self.private_invitation_detail.format(key=uuid_zero))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        assert response.json()["result"][0]["message"] == InvitationDoesNotExist.message

    async def test_private_invitation_accept_invitation_does_not_exist(self, client, tom, uuid_zero):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.post(self.accept_private_url.format(key=uuid_zero))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        assert response.json()["result"][0]["message"] == InvitationDoesNotExist.message

    async def test_send_invitation_to_reviewer_invitation_already_approved(
        self, client, invitation_revier_data, tom, applet_one
    ):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        # send an invite
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_revier_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        key = response.json()["result"]["key"]
        # accept invite
        await client.login(self.login_url, invitation_revier_data.email, "Test1234!")
        response = await client.post(self.accept_url.format(key=key))
        assert response.status_code == http.HTTPStatus.OK

        # resend invite
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_revier_data,
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["result"][0]["message"] == ManagerInvitationExist.message

    async def test_send_incorrect_role_to_invite_managers(self, client, invitation_manager_data, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = invitation_manager_data.dict()
        data["role"] = "notvalid"
        resp = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            data,
        )
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        emsg = "value is not a valid enumeration member; " "permitted: 'manager', 'coordinator', 'editor'"
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == emsg

    async def test_invite_reviewer_with_respondent_does_not_exist(
        self, client, invitation_revier_data, tom, applet_one, uuid_zero
    ):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        invitation_revier_data.respondents = [uuid_zero]
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_revier_data,
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == RespondentDoesNotExist.message

    @pytest.mark.parametrize(
        "url,method",
        (("accept_url", "post"), ("decline_url", "delete")),
    )
    async def test_accept_or_decline_already_processed_invitation(
        self, client, url, method, invitation_manager_data, tom, applet_one
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        # Send an invite
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        invitation_key = response.json()["result"]["key"]
        resp = await client.login(
            self.login_url,
            invitation_manager_data.email,
            "Test1234!",
        )
        # Accept invite
        client_method = getattr(client, method)
        resp = await client_method(getattr(self, url).format(key=invitation_key))
        assert resp.status_code == http.HTTPStatus.OK
        # Accept one more time
        client_method = getattr(client, method)
        resp = await client_method(getattr(self, url).format(key=invitation_key))
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
