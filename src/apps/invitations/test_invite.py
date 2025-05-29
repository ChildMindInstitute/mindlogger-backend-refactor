import http
import json
import re
import uuid
from typing import Any, Literal

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
    InvitationLanguage,
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
from apps.shared.test.client import TestClient
from apps.subjects.crud import SubjectsCrud
from apps.subjects.domain import Subject, SubjectCreate
from apps.subjects.services import SubjectsService
from apps.users import UserSchema
from apps.users.domain import User, UserCreate, UserCreateRequest
from apps.workspaces.domain.constants import UserPinRole
from apps.workspaces.errors import AppletInviteAccessDenied
from apps.workspaces.service.user_access import UserAccessService
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture
async def applet_one_with_public_link(session: AsyncSession, applet_one: AppletFull, tom: User):
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet_one.id, CreateAccessLink(require_login=False))
    applet = await srv.get_full_applet(applet_one.id)
    assert applet.link is not None
    return applet


@pytest.fixture
async def applet_one_with_link(session: AsyncSession, applet_one: AppletFull, tom: User):
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet_one.id, CreateAccessLink(require_login=True))
    applet = await srv.get_full_applet(applet_one.id)
    assert applet.link is not None
    return applet


@pytest.fixture
async def applet_one_lucy_manager(session: AsyncSession, applet_one: AppletFull, tom: User, lucy: User) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.MANAGER)
    return applet_one


@pytest.fixture
async def applet_one_lucy_coordinator(
    session: AsyncSession, applet_one: AppletFull, tom: User, lucy: User
) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.COORDINATOR)
    return applet_one


@pytest.fixture
async def applet_one_lucy_respondent(
    session: AsyncSession, applet_one: AppletFull, tom: User, lucy: User
) -> AppletFull:
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
def subject_ids(tom: User, tom_applet_one_subject: Subject) -> list[uuid.UUID]:
    return [tom_applet_one_subject.id]


@pytest.fixture
def invitation_base_data(user_create: UserCreate) -> dict[str, str | EmailStr]:
    return dict(
        email=user_create.email, first_name=user_create.first_name, last_name=user_create.last_name, language="en"
    )


@pytest.fixture
def invitation_manager_data(invitation_base_data: dict[str, str | EmailStr]) -> InvitationManagersRequest:
    return InvitationManagersRequest(**invitation_base_data, role=ManagersRole.MANAGER, title="PHD")


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
        **invitation_base_data, secret_user_id=str(uuid.uuid4()), nickname=str(uuid.uuid4()), tag="respondentTag"
    )


@pytest.fixture
def invitation_reviewer_data(invitation_base_data, subject_ids) -> InvitationReviewerRequest:
    return InvitationReviewerRequest(**invitation_base_data, subjects=subject_ids)


@pytest.fixture
def shell_create_data():
    return dict(
        language="en",
        firstName="firstName",
        lastName="lastName",
        secretUserId="secretUserId",
        nickname="nickname",
        tag="tag",
    )


@pytest.fixture
async def applet_one_shell_account(session: AsyncSession, applet_one: AppletFull, tom: User) -> Subject:
    return await SubjectsService(session, tom.id).create(
        SubjectCreate(
            applet_id=applet_one.id,
            creator_id=tom.id,
            first_name="Shell",
            last_name="Account",
            nickname="shell-account-0",
            tag="shell-account-0-tag",
            secret_user_id=f"{uuid.uuid4()}",
        )
    )


@pytest.fixture
async def applet_one_lucy_subject(session: AsyncSession, applet_one: AppletFull, tom: User, lucy: User) -> Subject:
    return await SubjectsService(session, tom.id).create(
        SubjectCreate(
            applet_id=applet_one.id,
            creator_id=lucy.id,
            first_name="Shell",
            last_name="Account",
            nickname="shell-account-0",
            secret_user_id=f"{uuid.uuid4()}",
        )
    )


def message_language(message_body: str):
    assert message_body
    match_result = re.search(r"<span data-language=\"([^\"]*)\"></span>", message_body)
    assert match_result
    return match_result.group(1)


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
    shell_acc_create_url = f"{invitation_list}/{{applet_id}}/shell-account"
    shell_acc_invite_url = f"{invitation_list}/{{applet_id}}/subject"

    @pytest.mark.parametrize("invite_language", ["en", "fr", "el"])
    @pytest.mark.parametrize(
        "inviter_type,invitee_type,invite_status",
        [
            ("admin", "manager", http.HTTPStatus.OK),
            ("admin", "coordinator", http.HTTPStatus.OK),
            ("admin", "editor", http.HTTPStatus.OK),
            ("admin", "reviewer", http.HTTPStatus.OK),
            ("admin", "respondent", http.HTTPStatus.OK),
            ("manager", "manager", http.HTTPStatus.OK),
            ("manager", "coordinator", http.HTTPStatus.OK),
            ("manager", "editor", http.HTTPStatus.OK),
            ("manager", "reviewer", http.HTTPStatus.OK),
            ("manager", "respondent", http.HTTPStatus.OK),
            ("coordinator", "respondent", http.HTTPStatus.OK),
            ("coordinator", "reviewer", http.HTTPStatus.OK),
            ("coordinator", "manager", http.HTTPStatus.FORBIDDEN),
            ("editor", "respondent", http.HTTPStatus.FORBIDDEN),
        ],
    )
    async def test_invite_existing_user(
        self,
        client: TestClient,
        session: AsyncSession,
        tom: User,
        lucy: User,
        user: User,
        applet_one: AppletFull,
        invitation_manager_data: InvitationManagersRequest,
        invitation_coordinator_data: InvitationManagersRequest,
        invitation_editor_data: InvitationManagersRequest,
        invitation_reviewer_data: InvitationReviewerRequest,
        invitation_respondent_data: InvitationRespondentRequest,
        mailbox: TestMail,
        invite_language: str,
        inviter_type: str,
        invitee_type: str,
        invite_status: str,
    ):
        if inviter_type == "admin":
            client.login(tom)
        elif inviter_type == "manager":
            client.login(lucy)
            await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.MANAGER)
        elif inviter_type == "coordinator":
            client.login(lucy)
            await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.COORDINATOR)
        elif inviter_type == "editor":
            client.login(lucy)
            await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.EDITOR)
        else:
            raise Exception(f"Invalid inviter_type: {inviter_type}")

        payload: Any
        if invitee_type == "manager":
            url = self.invite_manager_url
            payload = invitation_manager_data
        elif invitee_type == "coordinator":
            url = self.invite_manager_url
            payload = invitation_coordinator_data
        elif invitee_type == "editor":
            url = self.invite_manager_url
            payload = invitation_editor_data
        elif invitee_type == "reviewer":
            url = self.invite_reviewer_url
            payload = invitation_reviewer_data
        elif invitee_type == "respondent":
            url = self.invite_respondent_url
            payload = invitation_respondent_data
        else:
            raise Exception(f"Invalid invitee_type: {invitee_type}")
        payload.language = InvitationLanguage(invite_language)

        response = await client.post(url.format(applet_id=str(applet_one.id)), payload)
        assert response.status_code == invite_status

        if invite_status == http.HTTPStatus.OK:
            assert response.json()["result"]["userId"] == str(user.id)
            assert len(mailbox.mails) == 1
            assert message_language(mailbox.mails[0].body) == invite_language
            assert len(mailbox.mails[0].recipients) == 1
            assert mailbox.mails[0].recipients[0] == payload.email

            if invitee_type == "respondent":
                assert response.json()["result"]["userId"] == str(user.id)
                assert response.json()["result"]["tag"] is not None
                assert response.json()["result"]["tag"] == payload.tag

    @pytest.mark.parametrize("invite_language", ["en", "fr"])
    @pytest.mark.parametrize("invitee_type", ["manager", "coordinator", "editor", "reviewer", "respondent"])
    async def test_invite_new_user(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        invitation_manager_data: InvitationManagersRequest,
        invitation_coordinator_data: InvitationManagersRequest,
        invitation_editor_data: InvitationManagersRequest,
        invitation_reviewer_data: InvitationReviewerRequest,
        invitation_respondent_data: InvitationRespondentRequest,
        mailbox: TestMail,
        invite_language: str,
        invitee_type: str,
    ):
        client.login(tom)

        payload: Any
        if invitee_type == "manager":
            payload = invitation_manager_data
            url = self.invite_manager_url
        elif invitee_type == "coordinator":
            payload = invitation_coordinator_data
            url = self.invite_manager_url
        elif invitee_type == "editor":
            payload = invitation_editor_data
            url = self.invite_manager_url
        elif invitee_type == "reviewer":
            payload = invitation_reviewer_data
            url = self.invite_reviewer_url
        elif invitee_type == "respondent":
            payload = invitation_respondent_data
            url = self.invite_respondent_url
        else:
            raise Exception(f"Invalid invitee_type: {invitee_type}")
        payload.email = EmailStr(f"new{invitation_manager_data.email}")
        payload.language = InvitationLanguage(invite_language)

        response = await client.post(
            url.format(applet_id=str(applet_one.id)),
            payload,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert not response.json()["result"]["userId"]
        assert len(mailbox.mails) == 1
        assert message_language(mailbox.mails[0].body) == invite_language

    async def test_invitation_list(self, client: TestClient, tom: User):
        client.login(tom)

        response = await client.get(self.invitation_list)
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.json()["result"]) == 3

    async def test_applets_invitation_list(self, client: TestClient, tom: User, applet_one: AppletFull):
        client.login(tom)

        response = await client.get(
            self.invitation_list,
            dict(appletId=str(applet_one.id)),
        )
        assert response.status_code == http.HTTPStatus.OK

        assert len(response.json()["result"]) == 2

    async def test_invitation_retrieve(
        self, client: TestClient, applet_one: AppletFull, lucy: User, applet_one_lucy_subject: Subject
    ):
        client.login(lucy)
        response = await client.get(self.invitation_detail.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6"))
        assert response.status_code == http.HTTPStatus.OK

        assert response.json()["result"]["appletId"] == str(applet_one.id)
        assert response.json()["result"]["role"] == Role.MANAGER
        assert response.json()["result"]["firstName"] == "first_name"
        assert response.json()["result"]["lastName"] == "last_name"
        assert response.json()["result"]["tag"] is not None
        assert response.json()["result"]["title"] == "PHD"

    async def test_private_invitation_retrieve(self, client: TestClient, applet_one_with_link: AppletFull, lucy: User):
        client.login(lucy)

        response = await client.get(self.private_invitation_detail.format(key=applet_one_with_link.link))
        assert response.status_code == http.HTTPStatus.OK

        assert response.json()["result"]["appletId"] == str(applet_one_with_link.id)
        assert response.json()["result"]["role"] == Role.RESPONDENT

    async def test_admin_invite_respondent_duplicate_pending_secret_id(
        self,
        client: TestClient,
        invitation_respondent_data: InvitationRespondentRequest,
        tom: User,
        applet_one: AppletFull,
    ):
        client.login(tom)
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        invitation_respondent_data.email = EmailStr("patric1@gmail.com")
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == NonUniqueValue.message
        assert result[0]["path"] == ["body", "secretUserId"]

    async def test_invitation_accept_and_absorb_roles(
        self,
        session: AsyncSession,
        client: TestClient,
        lucy: User,
        applet_one_lucy_roles: AppletFull,
        applet_one: AppletFull,
    ):
        client.login(lucy)

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

    async def test_private_invitation_accept(
        self, session: AsyncSession, client: TestClient, lucy: User, applet_one_with_link: AppletFull
    ):
        client.login(lucy)

        response = await client.post(self.accept_private_url.format(key=applet_one_with_link.link))
        assert response.status_code == http.HTTPStatus.OK
        access = await UserAppletAccessCRUD(session).get_by_roles(
            user_id=lucy.id,
            applet_id=applet_one_with_link.id,
            ordered_roles=[Role.RESPONDENT],
        )
        assert access
        assert access.role == Role.RESPONDENT.value

    async def test_invitation_accept_invitation_does_not_exists(self, client: TestClient, tom: User, uuid_zero):
        client.login(tom)

        response = await client.post(self.accept_url.format(key=uuid_zero))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_invitation_decline(self, client: TestClient, lucy: User):
        client.login(lucy)

        response = await client.delete(self.decline_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da6"))
        assert response.status_code == http.HTTPStatus.OK

    async def test_invitation_decline_wrong_invitation_does_not_exists(self, client: TestClient, tom: User):
        client.login(tom)

        response = await client.delete(self.decline_url.format(key="6a3ab8e6-f2fa-49ae-b2db-197136677da9"))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        assert response.json()["result"][0]["message"] == InvitationDoesNotExist.message

    @pytest.mark.parametrize("role", (Role.MANAGER, Role.COORDINATOR, Role.EDITOR))
    async def test_manager_invite_if_duplicate_email_and_role_not_accepted(
        self,
        client: TestClient,
        role: Role,
        invitation_manager_data: InvitationManagersRequest,
        applet_one_lucy_manager: AppletFull,
        lucy: User,
        mailbox: TestMail,
    ):
        client.login(lucy)
        invitation_manager_data.role = ManagersRole(role)
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
        assert len(mailbox.mails) == 2
        assert message_language(mailbox.mails[0].body) == "en"
        assert message_language(mailbox.mails[1].body) == "en"

    async def test_admin_invite_respondent_fail_if_duplicate_email(
        self,
        client: TestClient,
        invitation_respondent_data: InvitationRespondentRequest,
        tom: User,
        applet_one_lucy_respondent: AppletFull,
        lucy: User,
        mailbox: TestMail,
    ):
        client.login(tom)
        invitation_respondent_data.email = EmailStr(lucy.email_encrypted)
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one_lucy_respondent.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        res = json.loads(response.content)
        res = res["result"][0]
        assert res["message"] == RespondentInvitationExist.message
        assert len(mailbox.mails) == 0

    async def test_fail_if_invite_manager_on_editor_role(
        self,
        client: TestClient,
        invitation_editor_data: InvitationManagersRequest,
        tom: User,
        applet_one_lucy_manager: AppletFull,
        lucy: User,
        mailbox: TestMail,
    ):
        client.login(tom)
        invitation_editor_data.email = EmailStr(lucy.email_encrypted)
        response = await client.post(
            self.invite_manager_url.format(applet_id=applet_one_lucy_manager.id),
            invitation_editor_data,
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        res = json.loads(response.content)
        res = res["result"][0]
        assert res["message"] == ManagerInvitationExist.message
        assert len(mailbox.mails) == 0

    @pytest.mark.parametrize(
        "status,url,method",
        (
            (InvitationStatus.APPROVED, "accept_url", "post"),
            (InvitationStatus.DECLINED, "decline_url", "delete"),
        ),
    )
    async def test_new_user_accept_decline_invitation(
        self,
        session: AsyncSession,
        client: TestClient,
        user_create_data: UserCreateRequest,
        status: InvitationStatus,
        url: str,
        method: str,
        invitation_manager_data: InvitationManagersRequest,
        tom: User,
        applet_one: AppletFull,
    ) -> None:
        client.login(tom)
        new_email = f"new{invitation_manager_data.email}"
        invitation_manager_data.email = EmailStr(new_email)
        # Send an invite
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data.dict(),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert not response.json()["result"]["userId"]

        invitation_key = response.json()["result"]["key"]
        user_create_data.email = EmailStr(new_email)
        # An invited user creates an account
        resp = await client.post("/users", data=user_create_data.dict())
        assert resp.status_code == http.HTTPStatus.CREATED
        client.login(uuid.UUID(resp.json()["result"]["id"]))
        exp_user_id = resp.json()["result"]["id"]
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
        self,
        client: TestClient,
        user_create_data,
        invitation_manager_data: InvitationManagersRequest,
        tom: User,
        applet_one: AppletFull,
    ) -> None:
        client.login(tom)
        new_email = f"new{invitation_manager_data.email}"
        invitation_manager_data.email = EmailStr(new_email)
        # Send an invite
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert not response.json()["result"]["userId"]

        user_create_data.email = new_email
        # An invited user creates an account
        resp = await client.post("/users", data=user_create_data.dict())
        assert resp.status_code == http.HTTPStatus.CREATED
        client.login(uuid.UUID(resp.json()["result"]["id"]))
        exp_user_id = resp.json()["result"]["id"]

        # Update an invite
        client.login(tom)
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["userId"] == exp_user_id

    async def test_resend_invitation_with_updates_for_respondent_with_pending_invitation(
        self,
        session: AsyncSession,
        client: TestClient,
        invitation_respondent_data: InvitationRespondentRequest,
        tom: User,
        applet_one: AppletFull,
    ):
        client.login(tom)
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
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_resend_invitation_for_respondent_with_pending_invitation_only_last_key_valid(
        self,
        client: TestClient,
        invitation_respondent_data: InvitationRespondentRequest,
        tom: User,
        applet_one: AppletFull,
        user: User,
    ):
        client.login(tom)
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        old_key = response.json()["result"]["key"]

        invitation_respondent_data.secret_user_id = str(uuid.uuid4())
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        new_key = response.json()["result"]["key"]
        client.login(user)

        response = await client.get(self.invitation_detail.format(key=old_key))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

        # we use invitation detail url for tests, because sninny atomic
        # does not work correct in tests.
        response = await client.get(self.invitation_detail.format(key=new_key))
        assert response.status_code == http.HTTPStatus.OK

    async def test_send_many_pending_invitations_for_one_email_valid_only_last(
        self,
        client: TestClient,
        session: AsyncSession,
        invitation_coordinator_data: InvitationManagersRequest,
        invitation_editor_data: InvitationManagersRequest,
        invitation_manager_data: InvitationManagersRequest,
        invitation_respondent_data: InvitationRespondentRequest,
        invitation_reviewer_data: InvitationReviewerRequest,
        tom: User,
        applet_one: AppletFull,
        user: User,
    ):
        client.login(tom)
        invitations_urls = [
            (invitation_coordinator_data, self.invite_manager_url),
            (invitation_editor_data, self.invite_manager_url),
            (invitation_manager_data, self.invite_manager_url),
            (invitation_respondent_data, self.invite_respondent_url),
            (invitation_reviewer_data, self.invite_reviewer_url),
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

        client.login(user)
        # Check first and last invitations to test that only last is valid
        response = await client.get(self.invitation_detail.format(key=keys[0]))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        response = await client.get(self.invitation_detail.format(key=keys[-1]))
        assert response.status_code == http.HTTPStatus.OK

    async def test_get_invitation_by_key_invitation_does_not_exist(
        self, client: TestClient, tom: User, uuid_zero: uuid.UUID
    ):
        client.login(tom)

        response = await client.get(self.invitation_detail.format(key=uuid_zero))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        assert response.json()["result"][0]["message"] == InvitationDoesNotExist.message

    @pytest.mark.parametrize(
        "url,method",
        (("decline_url", "delete"), ("accept_url", "post")),
    )
    async def test_get_invitation_by_key_already_accpted_declined(
        self,
        client: TestClient,
        url: Literal["decline_url", "accept_url"],
        method: Literal["delete", "post"],
        lucy: User,
    ):
        client.login(lucy)
        key = "6a3ab8e6-f2fa-49ae-b2db-197136677da6"
        client_method = getattr(client, method)
        url_ = getattr(self, url)
        response = await client_method(url_.format(key=key))
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(self.invitation_detail.format(key=key))
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == InvitationAlreadyProcessed.message

    async def test_get_private_invitation_by_link_does_not_exist(
        self, client: TestClient, tom: User, uuid_zero: uuid.UUID
    ):
        client.login(tom)

        response = await client.get(self.private_invitation_detail.format(key=uuid_zero))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        assert response.json()["result"][0]["message"] == InvitationDoesNotExist.message

    async def test_private_invitation_accept_invitation_does_not_exist(
        self, client: TestClient, tom: User, uuid_zero: uuid.UUID
    ):
        client.login(tom)

        response = await client.post(self.accept_private_url.format(key=uuid_zero))
        assert response.status_code == http.HTTPStatus.NOT_FOUND
        assert response.json()["result"][0]["message"] == InvitationDoesNotExist.message

    async def test_send_invitation_to_reviewer_invitation_already_approved(
        self,
        client: TestClient,
        invitation_reviewer_data: InvitationReviewerRequest,
        tom: User,
        applet_one: AppletFull,
        user: User,
    ):
        client.login(tom)
        # send an invite
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_reviewer_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        key = response.json()["result"]["key"]
        # accept invite
        client.login(user)
        response = await client.post(self.accept_url.format(key=key))
        assert response.status_code == http.HTTPStatus.OK

        # resend invite
        client.login(tom)
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_reviewer_data,
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["result"][0]["message"] == ManagerInvitationExist.message

    async def test_send_incorrect_role_to_invite_managers(
        self, client: TestClient, invitation_manager_data: InvitationManagersRequest, tom: User, applet_one: AppletFull
    ):
        client.login(tom)
        data = invitation_manager_data.dict()
        data["role"] = "notvalid"
        resp = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            data,
        )
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        emsg = "value is not a valid enumeration member; permitted: 'manager', 'coordinator', 'editor'"
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == emsg

    async def test_invite_reviewer_with_respondent_does_not_exist(
        self,
        client: TestClient,
        invitation_reviewer_data: InvitationReviewerRequest,
        tom: User,
        applet_one: AppletFull,
        uuid_zero: uuid.UUID,
    ):
        client.login(tom)
        invitation_reviewer_data.subjects = [uuid_zero]
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_reviewer_data,
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
        self,
        client: TestClient,
        url: str,
        method: str,
        invitation_manager_data: InvitationManagersRequest,
        tom: User,
        applet_one: AppletFull,
        user: User,
    ) -> None:
        client.login(tom)
        # Send an invite
        response = await client.post(
            self.invite_manager_url.format(applet_id=str(applet_one.id)),
            invitation_manager_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        invitation_key = response.json()["result"]["key"]
        client.login(user)
        # Accept invite
        client_method = getattr(client, method)
        resp = await client_method(getattr(self, url).format(key=invitation_key))
        assert resp.status_code == http.HTTPStatus.OK
        # Accept one more time
        client_method = getattr(client, method)
        resp = await client_method(getattr(self, url).format(key=invitation_key))
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST

    async def test_shell_create_account(
        self, client: TestClient, shell_create_data: dict, bob: User, applet_four: AppletFull
    ):
        client.login(bob)
        applet_id = str(applet_four.id)
        creator_id = str(bob.id)
        url = self.shell_acc_create_url.format(applet_id=applet_id)
        response = await client.post(url, shell_create_data)
        assert response.status_code == http.HTTPStatus.OK
        assert len(TestMail.mails) == 0
        payload = response.json()
        assert payload["result"]["appletId"] == applet_id
        assert payload["result"]["creatorId"] == creator_id
        assert payload["result"]["language"] == shell_create_data["language"]
        assert payload["result"]["tag"] == shell_create_data["tag"]

    @pytest.mark.parametrize(
        "shell_create",
        (
            dict(
                language="en",
                firstName="firstName",
                lastName="lastName",
                secretUserId="secretUserId",
                nickname="nickname",
            ),
            dict(
                language="en",
                firstName="firstName",
                lastName="lastName",
                secretUserId="secretUserId",
            ),
        ),
    )
    async def test_shell_invite(
        self, client: TestClient, session: AsyncSession, bob: User, applet_four: AppletFull, shell_create: dict
    ):
        client.login(bob)
        email = "mm@mail.com"
        applet_id = str(applet_four.id)
        url = self.shell_acc_create_url.format(applet_id=applet_id)
        response = await client.post(url, shell_create)
        subject = response.json()["result"]

        url = self.shell_acc_invite_url.format(applet_id=applet_id)
        response = await client.post(url, dict(subjectId=subject["id"], email=email, language="fr"))
        assert response.status_code == http.HTTPStatus.OK
        assert len(TestMail.mails) == 1
        subject_model = await SubjectsCrud(session).get_by_id(subject["id"])
        assert subject_model
        assert subject_model.email == email
        assert subject_model.language == "fr"

    async def test_shell_invite_no_language(
        self, client: TestClient, session: AsyncSession, shell_create_data: dict, bob: User, applet_four: AppletFull
    ):
        client.login(bob)
        email = "mm_english@mail.com"
        applet_id = str(applet_four.id)
        url = self.shell_acc_create_url.format(applet_id=applet_id)
        response = await client.post(url, shell_create_data)
        subject = response.json()["result"]

        url = self.shell_acc_invite_url.format(applet_id=applet_id)
        response = await client.post(url, dict(subjectId=subject["id"], email=email))
        assert response.status_code == http.HTTPStatus.OK
        assert len(TestMail.mails) == 1
        subject_model = await SubjectsCrud(session).get_by_id(subject["id"])
        assert subject_model
        assert subject_model.email == email
        assert subject_model.language == shell_create_data["language"]

    async def test_invite_and_accept_invitation_as_respondent(
        self,
        client: TestClient,
        session: AsyncSession,
        invitation_respondent_data: InvitationRespondentRequest,
        tom: User,
        applet_one: AppletFull,
        bill_bronson: User,
    ):
        subject_crud = SubjectsCrud(session)
        applet_id = applet_one.id
        user_email = bill_bronson.email_encrypted
        user_id = tom.id
        # Create invitation to Mike
        client.login(tom)
        invitation_respondent_data.email = EmailStr(user_email)
        subjects_on_applet0 = await subject_crud.count(applet_id=applet_id)
        response = await client.post(
            self.invite_respondent_url.format(applet_id=applet_id),
            invitation_respondent_data.dict(),
        )
        assert response.status_code == http.HTTPStatus.OK
        subjects_on_applet1 = await subject_crud.count(applet_id=applet_id)
        assert subjects_on_applet1 == (subjects_on_applet0 + 1)
        invitation = response.json()["result"]
        # Login as Mike and accept invitation
        client.login(bill_bronson)
        url_accept = self.accept_url.format(key=invitation["key"])
        response = await client.post(url_accept)
        assert response.status_code == http.HTTPStatus.OK
        subject = await subject_crud.get(user_id, applet_id)
        assert subject
        subjects_on_applet2 = await subject_crud.count(applet_id=applet_id)
        assert subjects_on_applet2 == subjects_on_applet1

    async def test_invite_and_accept_invitation_as_manager(
        self,
        client: TestClient,
        session: AsyncSession,
        invitation_manager_data: InvitationManagersRequest,
        tom: User,
        user: UserSchema,
        applet_one: AppletFull,
    ):
        subject_crud = SubjectsCrud(session)
        applet_id = applet_one.id
        # Create invitation to User
        client.login(tom)
        invitation_manager_data.email = user.email_encrypted
        subjects_on_applet0 = await subject_crud.count(applet_id=applet_id)
        response = await client.post(
            self.invite_manager_url.format(applet_id=applet_id),
            invitation_manager_data.dict(),
        )
        assert response.status_code == http.HTTPStatus.OK
        subjects_on_applet1 = await subject_crud.count(applet_id=applet_id)
        assert subjects_on_applet1 == subjects_on_applet0
        invitation = response.json()["result"]
        # Login as Mike and accept invitation
        client.login(user)
        url_accept = self.accept_url.format(key=invitation["key"])
        response = await client.post(url_accept)
        assert response.status_code == http.HTTPStatus.OK
        subject = await subject_crud.get(user.id, applet_id)
        assert subject
        subjects_on_applet2 = await subject_crud.count(applet_id=applet_id)
        assert subjects_on_applet2 == (subjects_on_applet1 + 1)

    async def test_private_invitation_accept_create_subject(
        self, client: TestClient, session: AsyncSession, user: User, applet_one_with_link: AppletFull
    ):
        assert applet_one_with_link.link
        subject_crud = SubjectsCrud(session)
        applet_id = applet_one_with_link.id
        client.login(user)
        count0 = await subject_crud.count(applet_id=applet_id)
        response = await client.post(self.accept_private_url.format(key=str(applet_one_with_link.link)))
        assert response.status_code == http.HTTPStatus.OK
        count1 = await subject_crud.count(applet_id=applet_id)
        assert (count0 + 1) == count1
        subject = subject_crud.get(user.id, applet_id)
        assert subject

    async def test_move_pins_from_subject_to_user(
        self,
        client: TestClient,
        session: AsyncSession,
        tom: User,
        bob: User,
        shell_create_data: dict,
        applet_one: AppletFull,
    ):
        client.login(tom)
        applet_id = str(applet_one.id)
        url = self.shell_acc_create_url.format(applet_id=applet_id)
        response = await client.post(url, shell_create_data)
        subject = response.json()["result"]
        url = self.shell_acc_invite_url.format(applet_id=applet_id)

        await UserAccessService(session, tom.id).pin(
            tom.id, UserPinRole.respondent, subject_id=uuid.UUID(subject["id"])
        )

        response = await client.post(url, dict(subjectId=subject["id"], email=bob.email_encrypted))
        assert response.status_code == http.HTTPStatus.OK
        assert len(TestMail.mails) == 1

        invitation = response.json()["result"]
        client.login(bob)
        url_accept = self.accept_url.format(key=invitation["key"])
        response = await client.post(url_accept)
        assert response.status_code == http.HTTPStatus.OK

        pins = await UserAppletAccessCRUD(session).get_workspace_pins(tom.id)
        assert pins[0].pinned_user_id == bob.id

    async def test_cant_create_invitation_with_same_secret_id_as_shell_account(
        self,
        client: TestClient,
        session: AsyncSession,
        applet_one: AppletFull,
        applet_one_shell_account: Subject,
        tom: User,
        invitation_respondent_data: InvitationRespondentRequest,
    ):
        client.login(tom)
        invitation_respondent_data.secret_user_id = applet_one_shell_account.secret_user_id
        response = await client.post(
            self.invite_respondent_url.format(applet_id=str(applet_one.id)),
            invitation_respondent_data.dict(),
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        payload = response.json()
        assert payload
        assert payload["result"][0]["message"] == NonUniqueValue().error

    async def test_shell_update_email_on_accept(
        self,
        client: TestClient,
        session: AsyncSession,
        bob: User,
        lucy: User,
        applet_four: AppletFull,
        shell_create_data: dict,
    ):
        client.login(bob)
        applet_id = str(applet_four.id)
        url = self.shell_acc_create_url.format(applet_id=applet_id)
        response = await client.post(url, shell_create_data)
        subject = response.json()["result"]

        url = self.shell_acc_invite_url.format(applet_id=applet_id)
        response = await client.post(url, dict(subjectId=subject["id"], email=lucy.email_encrypted))

        assert response.status_code == http.HTTPStatus.OK
        assert len(TestMail.mails) == 1
        invitation_key = response.json()["result"]["key"]

        # Change email for subject directly
        crud = SubjectsCrud(session)
        subject_model = await crud.get_by_id(subject["id"])
        assert subject_model
        subject_model.email = "mm2@mail.com"
        await crud._update_one("id", subject_model.id, subject_model)
        subject_model = await crud.get_by_id(subject["id"])
        assert subject_model
        assert subject_model.email != lucy.email_encrypted

        # Accept invite and check that subject have email from invite
        client.login(lucy)
        response = await client.post(self.accept_url.format(key=invitation_key))
        assert response.status_code == http.HTTPStatus.OK
        subject_model = await crud.get_by_id(subject["id"])
        assert subject_model
        assert subject_model.email == lucy.email_encrypted

    async def test_shell_reinvite(
        self,
        client: TestClient,
        session: AsyncSession,
        bob: User,
        lucy: User,
        applet_four: AppletFull,
        shell_create_data: dict,
        mailbox: TestMail,
    ):
        client.login(bob)
        response = await client.post(self.shell_acc_create_url.format(applet_id=str(applet_four.id)), shell_create_data)
        assert response.status_code == http.HTTPStatus.OK
        subject = response.json()["result"]
        assert subject

        response = await client.post(
            self.shell_acc_invite_url.format(applet_id=str(applet_four.id)),
            dict(subjectId=subject["id"], email=lucy.email_encrypted),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(mailbox.mails) == 1
        assert message_language(mailbox.mails[0].body) == "en"
        invitation_key = response.json()["result"]["key"]
        assert invitation_key

        client.login(lucy)
        response = await client.post(self.accept_url.format(key=invitation_key))
        assert response.status_code == http.HTTPStatus.OK

        client.login(bob)
        response = await client.post(
            self.shell_acc_create_url.format(applet_id=str(applet_four.id)),
            {**shell_create_data, "secretUserId": f"{uuid.uuid4()}"},
        )
        assert response.status_code == http.HTTPStatus.OK
        subject = response.json()["result"]
        assert subject

        response = await client.post(
            self.shell_acc_invite_url.format(applet_id=str(applet_four.id)),
            dict(subjectId=subject["id"], email=lucy.email_encrypted),
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        message = response.json()["result"][0]["message"]
        assert message == RespondentInvitationExist.message

    async def test_respondent_can_NOT_invite_new_reviewer_for_a_specific_respondent(
        self,
        client: TestClient,
        invitation_reviewer_data: InvitationReviewerRequest,
        lucy: User,
        applet_one: AppletFull,
    ):
        client.login(lucy)
        # try to invite a reviewer for a specific respondent
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_reviewer_data,
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result= response.json()["result"]
        assert response.json()["result"][0]["message"] == AppletInviteAccessDenied.message

    async def test_editor_can_NOT_invite_new_reviewer_for_a_specific_respondent(
        self,
        client: TestClient,
        invitation_reviewer_data: InvitationReviewerRequest,
        mike: User,
        applet_one: AppletFull,
    ):
        client.login(mike)
        # try to invite a reviewer for a specific respondent
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_reviewer_data,
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN
        assert response.json()["result"][0]["message"] == AppletInviteAccessDenied.message

    async def test_coordinator_can_NOT_invite_new_reviewer_for_a_specific_respondent(
        self,
        client: TestClient,
        invitation_reviewer_data: InvitationReviewerRequest,
        bob: User,
        applet_one: AppletFull,
    ):
        client.login(bob)
        # try to invite a reviewer for a specific respondent
        response = await client.post(
            self.invite_reviewer_url.format(applet_id=str(applet_one.id)),
            invitation_reviewer_data,
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN
        assert response.json()["result"][0]["message"] == AppletInviteAccessDenied.message