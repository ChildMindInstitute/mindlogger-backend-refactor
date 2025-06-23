import datetime
import http
import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.domain import AppletAnswerCreate, ClientMeta, ItemAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain import Role
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.service.applet import AppletService
from apps.invitations.domain import InvitationManagersRequest, InvitationRespondentRequest
from apps.invitations.services import InvitationsService
from apps.shared.enums import Language
from apps.shared.query_params import QueryParams
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.constants import SubjectStatus
from apps.subjects.domain import Subject, SubjectCreate
from apps.subjects.services import SubjectsService
from apps.users import User, UserSchema, UsersCRUD
from apps.workspaces.domain.workspace import WorkspaceApplet
from apps.workspaces.errors import AppletAccessDenied, InvalidAppletIDFilter
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from apps.workspaces.service.workspace import WorkspaceService


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
async def applet_not_in_folder(session: AsyncSession, tom, applet_minimal_data: AppletCreate):
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "applet not in folder"
    data.description = {Language.ENGLISH: data.display_name}
    applet = await AppletService(session, tom.id).create(data)
    return applet


@pytest.fixture
async def applet_one_user_respondent(session: AsyncSession, applet_one: AppletFull, tom, user) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(user.id, Role.RESPONDENT)
    return applet_one


@pytest.fixture
async def applet_three_tom_respondent(session: AsyncSession, applet_three: AppletFull, tom, lucy) -> AppletFull:
    await UserAppletAccessService(session, lucy.id, applet_three.id).add_role(tom.id, Role.RESPONDENT)
    return applet_three


@pytest.fixture
async def applet_three_user_respondent(session: AsyncSession, applet_three: AppletFull, lucy, user) -> AppletFull:
    await UserAppletAccessService(session, lucy.id, applet_three.id).add_role(user.id, Role.RESPONDENT)
    return applet_three


@pytest.fixture
async def applet_one_lucy_roles(
    applet_one_lucy_respondent: AppletFull,
    applet_one_lucy_coordinator: AppletFull,
    applet_one_lucy_editor: AppletFull,
    applet_one_lucy_manager: AppletFull,
) -> list[AppletFull]:
    return [applet_one_lucy_respondent, applet_one_lucy_coordinator, applet_one_lucy_editor, applet_one_lucy_manager]


@pytest.fixture
async def applet_one_bob_coordinator(session: AsyncSession, applet_one: AppletFull, tom, bob) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(bob.id, Role.COORDINATOR)
    return applet_one


@pytest.fixture
async def applet_one_bob_coordinator_reviewer(session: AsyncSession, applet_one: AppletFull, tom, bob) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(bob.id, Role.COORDINATOR)
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(bob.id, Role.REVIEWER)
    return applet_one


@pytest.fixture
async def applet_one_shell_account(session: AsyncSession, applet_one: AppletFull, tom: User) -> Subject:
    return await SubjectsService(session, tom.id).create(
        SubjectCreate(
            applet_id=applet_one.id,
            creator_id=tom.id,
            first_name="Shell",
            last_name="Account",
            nickname="shell-account-0",
            secret_user_id=f"{uuid.uuid4()}",
            email="shell@mail.com",
        )
    )


@pytest.fixture
async def tom_applets(session: AsyncSession, tom: UserSchema):
    params = QueryParams()
    return await WorkspaceService(session, tom.id).get_workspace_applets(tom.id, "en", params)


@pytest.fixture
async def tom_answer_applet_one(session, tom: User, applet_one: AppletFull):
    subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_one.id)
    items_ids = []
    activity = applet_one.activities[0]
    for item in activity.items:
        items_ids.append(item.id)
    assert subject
    activity_answer = AppletAnswerCreate(
        applet_id=applet_one.id,
        version=applet_one.version,
        submit_id=uuid.uuid4(),
        activity_id=activity.id,
        answer=ItemAnswerCreate(
            item_ids=items_ids,
            start_time=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            end_time=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        ),
        client=ClientMeta(app_id="web", app_version="1.1.0", width=800, height=600),
        target_subject_id=subject.id,
        source_subject_id=subject.id,
        consent_to_share=False,
    )
    return await AnswerService(session, tom.id).create_answer(activity_answer)


@pytest.fixture
async def applet_one_shell_has_pending_invitation(session, tom: User, user: User, applet_one: AppletFull):
    subject = await SubjectsService(session, tom.id).create(
        SubjectCreate(
            applet_id=applet_one.id,
            creator_id=tom.id,
            first_name="Invited",
            last_name="Shell",
            nickname="shell-account-invited",
            secret_user_id=f"{uuid.uuid4()}",
        )
    )
    schema = InvitationRespondentRequest(
        email=user.email_encrypted,
        first_name=user.first_name,
        last_name=user.last_name,
        language="en",
        secret_user_id=f"{uuid.uuid4()}",
    )
    assert subject.id
    await InvitationsService(session, tom).send_respondent_invitation(applet_one.id, schema, subject)
    return subject


@pytest.fixture
async def applet_one_manager_has_pending_invitation(session, tom: User, user: User, applet_one: AppletFull):
    schema = InvitationManagersRequest(
        email=user.email_encrypted,
        first_name=user.first_name,
        last_name=user.last_name,
        language="en",
        role=Role.MANAGER,
        title="test",
    )
    result = await InvitationsService(session, tom).send_managers_invitation(applet_one.id, schema)

    return result


class TestWorkspaces(BaseTest):
    fixtures = [
        "folders/fixtures/folders.json",
        "invitations/fixtures/invitations.json",
        "workspaces/fixtures/workspaces.json",
        "folders/fixtures/folders_applet.json",
    ]

    login_url = "/auth/login"
    workspaces_list_url = "/workspaces"
    workspaces_detail_url = f"{workspaces_list_url}/{{owner_id}}"
    workspaces_priority_role_url = f"{workspaces_detail_url}/priority_role"
    workspace_roles_url = f"{workspaces_detail_url}/roles"

    workspace_applets_url = f"{workspaces_detail_url}/applets"
    search_workspace_applets_url = f"{workspace_applets_url}/search/{{text}}"
    workspace_folder_applets_url = f"{workspaces_detail_url}/folders/{{folder_id}}/applets"

    workspace_applets_detail_url = f"{workspace_applets_url}/{{applet_id}}"
    applet_respondent_url = f"{workspace_applets_detail_url}/respondents/{{respondent_id}}"
    workspace_respondents_url = f"{workspaces_detail_url}/respondents"
    workspace_applet_respondents_list = "/workspaces/{owner_id}/applets/{applet_id}/respondents"
    workspace_respondent_applet_accesses = f"{workspace_respondents_url}/{{respondent_id}}/accesses"
    workspace_managers_url = f"{workspaces_detail_url}/managers"
    workspace_applet_managers_list = "/workspaces/{owner_id}/applets/{applet_id}/managers"
    workspace_manager_accesses_url = f"{workspace_managers_url}/{{manager_id}}/accesses"
    remove_manager_access = f"{workspaces_list_url}/managers/removeAccess"
    remove_respondent_access = "/applets/respondent/removeAccess"
    workspace_respondents_pin = "/workspaces/{owner_id}/respondents/{user_id}/pin"
    workspace_subject_pin = "/workspaces/{owner_id}/subjects/{subject_id}/pin"
    workspace_managers_pin = "/workspaces/{owner_id}/managers/{user_id}/pin"
    workspace_get_applet_respondent = "/workspaces/{owner_id}/applets/{applet_id}/respondents/{respondent_id}"

    @pytest.mark.usefixtures("applet_three")
    async def test_user_workspace_list(self, client, lucy):
        client.login(lucy)

        response = await client.get(self.workspaces_list_url)
        assert response.status_code == 200, response.json()
        res = response.json()
        assert len(res["result"]) == 1
        assert res["count"] == 1
        assert set(res["result"][0].keys()) == {"useArbitrary", "workspaceName", "ownerId"}
        assert res["result"][0]["useArbitrary"] is False

    async def test_user_workspace_list_super_admin(self, client, superadmin):
        client.login(superadmin)

        response = await client.get(self.workspaces_list_url)
        assert response.status_code == 200, response.json()
        # TODO replace 3 with count from database or similar
        # 1 - superadmin and 2 from json fixtures
        assert len(response.json()["result"]) == 3

    async def test_user_workspace_retrieve_without_managers(self, client, lucy):
        client.login(lucy)

        response = await client.get(self.workspaces_detail_url.format(owner_id=lucy.id))
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == "Lucy Gabel Test"
        assert response.json()["result"]["hasManagers"] is False

    async def test_get_users_priority_role_in_workspace(self, client, tom, lucy, applet_one_lucy_coordinator):
        client.login(lucy)

        response = await client.get(self.workspaces_priority_role_url.format(owner_id=tom.id))
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["role"] == Role.COORDINATOR

    async def test_get_users_priority_role_in_workspace_super_admin(self, client, tom, superadmin):
        client.login(superadmin)

        response = await client.get(self.workspaces_priority_role_url.format(owner_id=tom.id))
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["role"] == Role.SUPER_ADMIN

    async def test_workspace_roles_retrieve(
        self, client, tom, lucy, applet_one_lucy_respondent, applet_one_lucy_manager, applet_one
    ):
        client.login(lucy)

        response = await client.get(self.workspace_roles_url.format(owner_id=tom.id))
        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        roles = data.get(str(applet_one.id))
        assert roles == [Role.MANAGER, Role.RESPONDENT]

    async def test_workspace_roles_with_super_admin_retrieve(self, client, tom, session, applet_one):
        # TODO: Remove later. Do it now just for this test while we have JSON fixtures
        crud = UsersCRUD(session)
        await crud.update_by_id(tom.id, UserSchema(is_super_admin=True))
        await session.commit()
        client.login(tom)

        response = await client.get(self.workspace_roles_url.format(owner_id=tom.id))
        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        roles = data.get(str(applet_one.id), [])
        assert roles == [Role.OWNER, Role.SUPER_ADMIN, Role.RESPONDENT]

    async def test_user_workspace_retrieve_with_managers(self, client, tom, applet_one_lucy_manager):
        client.login(tom)

        response = await client.get(self.workspaces_detail_url.format(owner_id=tom.id))
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == "Tom Isaak Test"
        assert response.json()["result"]["hasManagers"] is True

    async def test_user_workspace_retrieve_without_access(self, client, tom, lucy):
        client.login(tom)

        response = await client.get(self.workspaces_detail_url.format(owner_id=lucy.id))
        assert response.status_code == 403, response.json()

    async def test_workspace_applets_list(self, client, lucy):
        client.login(lucy)

        response = await client.get(
            self.workspace_applets_url.format(owner_id=lucy.id),
            dict(ordering="-displayName,created_at"),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 3
        assert response.json()["result"][0]["type"] == "folder"
        assert response.json()["result"][1]["type"] == "folder"
        assert response.json()["result"][2]["type"] == "applet"
        assert response.json()["result"][2]["role"] == Role.OWNER

    async def test_workspace_applets_search(self, client, lucy):
        client.login(lucy)

        response = await client.get(self.search_workspace_applets_url.format(owner_id=lucy.id, text="applet"))
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["displayName"] == "Applet 3"
        assert response.json()["result"][0]["role"] == Role.OWNER

    async def test_workspace_applets_list_by_folder_id_filter(self, client, tom, applet_not_in_folder):
        client.login(tom)

        response = await client.get(
            self.workspace_applets_url.format(owner_id=tom.id),
        )
        assert response.status_code == 200
        # Why 1 applet not in folder and 3 folders
        expected_count = 4
        assert response.json()["count"] == expected_count
        assert len(response.json()["result"]) == expected_count

    async def test_workspace_applets_detail(self, client, lucy, applet_one_lucy_manager):
        client.login(lucy)

        # check access not exists
        response = await client.get(
            self.workspace_applets_detail_url.format(
                owner_id=uuid.uuid4(),
                applet_id=str(applet_one_lucy_manager.id),
            )
        )
        assert response.status_code == 404

        response = await client.get(
            self.workspace_applets_detail_url.format(
                owner_id=lucy.id,
                applet_id=str(applet_one_lucy_manager.id),
            )
        )
        assert response.status_code == 200

    async def test_workspace_applets_respondent_update(self, client, tom, lucy, applet_one_lucy_respondent):
        client.login(tom)

        response = await client.post(
            self.applet_respondent_url.format(
                owner_id=tom.id,
                applet_id=str(applet_one_lucy_respondent.id),
                respondent_id=lucy.id,
            ),
            dict(
                nickname="New respondent",
                secret_user_id="f0dd4996-e0eb-461f-b2f8-ba873a674710",
            ),
        )
        assert response.status_code == 200

        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one_lucy_respondent.id),
            ),
            dict(
                role="respondent",
            ),
        )
        payload = response.json()
        assert payload["count"] == 2
        nicknames = []
        secret_ids = []
        for respondent in payload["result"]:
            nicknames += respondent.get("nicknames", [])
            secret_ids += respondent.get("secretIds", [])
        assert "New respondent" in nicknames
        assert "f0dd4996-e0eb-461f-b2f8-ba873a674710" in secret_ids

    async def test_wrong_workspace_applets_list(self, client, lucy):
        client.login(lucy)

        response = await client.get(self.workspace_applets_url.format(owner_id="00000000-0000-0000-0000-000000000000"))
        assert response.status_code == 404

    async def test_get_workspace_respondents(
        self,
        client: TestClient,
        tom: User,
        user: User,
        lucy: User,
        applet_one_lucy_respondent: AppletFull,
        applet_one_user_respondent: AppletFull,
        applet_three_tom_respondent: AppletFull,
        applet_three_user_respondent: AppletFull,
        applet_one_shell_account: Subject,
    ):
        client.login(tom)
        response = await client.get(
            self.workspace_respondents_url.format(owner_id=tom.id),
            dict(ordering="+nicknames"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 4  # lucy, tom, shell account, user
        assert data["count"] == len(data["result"])

        lucy_result = data["result"][0]
        shell_account_result = data["result"][1]
        tom_result = data["result"][2]
        user_result = data["result"][3]

        assert lucy_result["nicknames"]
        assert lucy_result["secretIds"]
        assert lucy_result["details"]
        assert tom_result["details"]

        def sorting_function(x: Any):
            return x["appletDisplayName"]

        lucy_result_details = sorted(lucy_result["details"], key=sorting_function)
        shell_account_result_details = sorted(shell_account_result["details"], key=sorting_function)
        tom_result_details = sorted(tom_result["details"], key=sorting_function)
        user_result_details = sorted(user_result["details"], key=sorting_function)

        # Lucy has a pending invitation to Applet 1
        assert lucy_result_details[0]["invitation"]  # Applet 1
        assert lucy_result_details[0]["invitation"]["status"] == "pending"

        assert lucy_result_details[0]["subjectFirstName"] == lucy.first_name
        assert lucy_result_details[0]["subjectLastName"] == lucy.last_name
        assert lucy_result_details[0]["subjectCreatedAt"]
        assert lucy_result_details[0]["roles"] == [Role.RESPONDENT]
        assert lucy_result_details[0]["teamMemberCanViewData"] is True

        # Tom has an approved invitation to Applet 1
        assert tom_result_details[0]["invitation"]  # Applet 1
        assert tom_result_details[0]["invitation"]["status"] == "approved"

        assert tom_result_details[0]["subjectFirstName"] == tom.first_name
        assert tom_result_details[0]["subjectLastName"] == tom.last_name
        assert tom_result_details[0]["subjectCreatedAt"]
        assert tom_result_details[0]["roles"] == [Role.OWNER, Role.RESPONDENT]
        assert tom_result_details[0]["teamMemberCanViewData"] is True

        # Tom has a pending invitation to Applet 2
        assert tom_result_details[1]["invitation"]  # Applet 2
        assert tom_result_details[1]["invitation"]["status"] == "pending"

        assert tom_result_details[1]["subjectFirstName"] == tom.first_name
        assert tom_result_details[1]["subjectLastName"] == tom.last_name
        assert tom_result_details[1]["subjectCreatedAt"]
        assert tom_result_details[1]["roles"] == [Role.OWNER, Role.RESPONDENT]
        assert tom_result_details[1]["teamMemberCanViewData"] is True

        # Check for the roles of the other participants
        assert shell_account_result_details[0]["roles"] == []  # Limited accounts have no roles
        assert user_result_details[0]["roles"] == [Role.RESPONDENT]

        # test manual, case-insensitive ordering by encrypted nicknames field
        assert set(data.keys()) == {"count", "result", "orderingFields"}
        assert data["orderingFields"] == [
            "isPinned",
            "secretIds",
            "tags",
            "createdAt",
            "status",
            "nicknames",
        ]
        assert lucy_result["nicknames"] == ["Lucy Gabel"]
        assert shell_account_result["nicknames"] == ["shell-account-0"]
        assert tom_result["nicknames"] == ["Tom Isaak"]
        assert user_result["nicknames"] == ["user test"]

        # test search
        access_id_0 = lucy_result_details[0]["accessId"]
        access_id_1 = tom_result_details[0]["accessId"]
        secret_user_id_0 = lucy_result["secretIds"][0]
        secret_user_id_1 = tom_result["secretIds"][0]
        search_params = {
            access_id_0: [secret_user_id_0[19:]],
            access_id_1: [secret_user_id_1],
        }
        for access_id, params in search_params.items():
            for val in params:
                response = await client.get(
                    self.workspace_respondents_url.format(owner_id=tom.id),
                    dict(search=val),
                )
                assert response.status_code == 200
                data = response.json()
                assert set(data.keys()) == {"count", "result", "orderingFields"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                access_ids = {detail["accessId"] for detail in result[0]["details"]}
                assert access_id in access_ids

    async def test_get_workspace_respondents_as_coordinator(
        self,
        client: TestClient,
        tom: User,
        bob: User,
        applet_one_lucy_respondent: AppletFull,
        applet_one_bob_coordinator: AppletFull,
        uuid_zero: uuid.UUID,
    ):
        client.login(bob)
        response = await client.get(
            self.workspace_respondents_url.format(owner_id=tom.id),
            dict(ordering="+nicknames"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2  # lucy, tom
        assert data["count"] == len(data["result"])

        lucy_result = data["result"][0]
        tom_result = data["result"][1]

        assert lucy_result["nicknames"]
        assert lucy_result["secretIds"]
        assert lucy_result["details"]
        assert tom_result["details"]

        lucy_result_details = lucy_result["details"]
        tom_result_details = sorted(tom_result["details"], key=lambda x: x["appletDisplayName"])

        assert tom_result_details[0]["teamMemberCanViewData"] is False
        assert lucy_result_details[0]["teamMemberCanViewData"] is False

    async def test_get_workspace_respondents_as_coordinator_and_reviewer(
        self,
        session: AsyncSession,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: Subject,
        bob: User,
        applet_one_lucy_respondent: AppletFull,
        applet_one_bob_coordinator_reviewer: AppletFull,
        uuid_zero: uuid.UUID,
    ):
        # Assign bob as a reviewer to tom
        await UserAppletAccessService(session, tom.id, applet_one_bob_coordinator_reviewer.id).set_subjects_for_review(
            reviewer_id=bob.id, applet_id=applet_one_bob_coordinator_reviewer.id, subjects=[tom_applet_one_subject.id]
        )

        client.login(bob)
        response = await client.get(
            self.workspace_respondents_url.format(owner_id=tom.id),
            dict(ordering="+nicknames"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2  # lucy, tom
        assert data["count"] == len(data["result"])

        lucy_result = data["result"][0]
        tom_result = data["result"][1]

        assert lucy_result["nicknames"]
        assert lucy_result["secretIds"]
        assert lucy_result["details"]
        assert tom_result["details"]

        lucy_result_details = lucy_result["details"]
        tom_result_details = sorted(tom_result["details"], key=lambda x: x["appletDisplayName"])

        assert tom_result_details[0]["teamMemberCanViewData"] is True
        assert lucy_result_details[0]["teamMemberCanViewData"] is False

    async def test_get_workspace_applet_respondents(
        self,
        client: TestClient,
        tom: User,
        lucy: User,
        applet_one: AppletFull,
        applet_one_lucy_respondent: AppletFull,
        uuid_zero: uuid.UUID,
    ):
        client.login(tom)
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["count"] == 2  # lucy, tom
        assert data["count"] == len(data["result"])

        lucy_result = data["result"][0]
        tom_result = data["result"][1]

        assert lucy_result["nicknames"]
        assert lucy_result["secretIds"]
        assert lucy_result["details"]
        assert tom_result["details"]

        lucy_result_details = lucy_result["details"]
        tom_result_details = tom_result["details"]

        # Lucy has a pending invitation to Applet 1
        assert lucy_result_details[0]["invitation"]  # Applet 1
        assert lucy_result_details[0]["invitation"]["status"] == "pending"

        assert lucy_result_details[0]["subjectFirstName"] == lucy.first_name
        assert lucy_result_details[0]["subjectLastName"] == lucy.last_name
        assert lucy_result_details[0]["subjectCreatedAt"]
        assert lucy_result_details[0]["roles"] == [Role.RESPONDENT]
        assert lucy_result_details[0]["teamMemberCanViewData"] is True

        # Tom has an approved invitation to Applet 1
        assert tom_result_details[0]["invitation"]  # Applet 1
        assert tom_result_details[0]["invitation"]["status"] == "approved"

        assert tom_result_details[0]["subjectFirstName"] == tom.first_name
        assert tom_result_details[0]["subjectLastName"] == tom.last_name
        assert tom_result_details[0]["subjectCreatedAt"]
        assert tom_result_details[0]["roles"] == [Role.OWNER, Role.RESPONDENT]
        assert tom_result_details[0]["teamMemberCanViewData"] is True

        # test search
        access_id = lucy_result_details[0]["accessId"]
        secret_id = lucy_result["secretIds"][0]
        subject_tag = lucy_result_details[0]["subjectTag"]
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
            dict(search=secret_id[19:]),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        result = data["result"]
        assert len(result) == 1
        assert access_id == data["result"][0]["details"][0]["accessId"]
        assert subject_tag == data["result"][0]["details"][0]["subjectTag"]
        assert data["result"][0]["details"][0]["subjectTag"] == "Team"

        # test search - there is no respondent

        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
            dict(search=str(uuid_zero)[19:]),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert not data["result"]

    async def test_get_workspace_applet_respondents_as_coordinator(
        self,
        client: TestClient,
        tom: User,
        bob: User,
        applet_one_lucy_respondent: AppletFull,
        applet_one_bob_coordinator: AppletFull,
        uuid_zero: uuid.UUID,
    ):
        client.login(bob)
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one_bob_coordinator.id),
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["count"] == 2  # lucy, tom
        assert data["count"] == len(data["result"])

        lucy_result = data["result"][0]
        tom_result = data["result"][1]

        assert lucy_result["nicknames"]
        assert lucy_result["secretIds"]
        assert lucy_result["details"]
        assert tom_result["details"]

        lucy_result_details = lucy_result["details"]
        tom_result_details = tom_result["details"]

        assert lucy_result_details[0]["teamMemberCanViewData"] is False
        assert tom_result_details[0]["teamMemberCanViewData"] is False

    async def test_get_workspace_applet_respondents_as_coordinator_and_reviewer(
        self,
        session: AsyncSession,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: Subject,
        bob: User,
        applet_one_lucy_respondent: AppletFull,
        applet_one_bob_coordinator_reviewer: AppletFull,
        uuid_zero: uuid.UUID,
    ):
        # Assign bob as a reviewer to tom
        await UserAppletAccessService(session, tom.id, applet_one_bob_coordinator_reviewer.id).set_subjects_for_review(
            reviewer_id=bob.id, applet_id=applet_one_bob_coordinator_reviewer.id, subjects=[tom_applet_one_subject.id]
        )

        client.login(bob)
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one_bob_coordinator_reviewer.id),
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["count"] == 2  # lucy, tom
        assert data["count"] == len(data["result"])

        lucy_result = data["result"][0]
        tom_result = data["result"][1]

        assert lucy_result["nicknames"]
        assert lucy_result["secretIds"]
        assert lucy_result["details"]
        assert tom_result["details"]

        lucy_result_details = lucy_result["details"]
        tom_result_details = tom_result["details"]

        assert lucy_result_details[0]["teamMemberCanViewData"] is False
        assert tom_result_details[0]["teamMemberCanViewData"] is True

    async def test_get_workspace_applet_respondents_filters(
        self,
        client,
        tom,
        applet_one,
        tom_applet_one_subject: SubjectCreate,
        lucy: User,
        applet_one_lucy_respondent,
    ):
        client.login(tom)

        url = self.workspace_applet_respondents_list.format(
            owner_id=tom.id,
            applet_id=str(applet_one.id),
        )

        response = await client.get(url, {"userId": str(lucy.id)})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["result"][0]["id"] == str(lucy.id)

        response = await client.get(url, {"respondentSecretId": str(tom_applet_one_subject.secret_user_id)})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["result"][0]["id"] == str(tom.id)
        assert data["result"][0]["secretIds"][0] == str(tom_applet_one_subject.secret_user_id)

    async def test_get_workspace_respondent_accesses(self, client, tom, lucy, applet_one_lucy_respondent):
        client.login(tom)
        response = await client.get(
            self.workspace_respondent_applet_accesses.format(
                owner_id=tom.id,
                respondent_id=lucy.id,
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1

    async def test_get_workspace_managers(self, client, tom, lucy, applet_one_lucy_manager):
        client.login(tom)
        response = await client.get(
            self.workspace_managers_url.format(owner_id=tom.id),
            dict(ordering="+email"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

        # test manual ordering by encrypted email field
        assert set(data.keys()) == {"count", "result", "orderingFields"}
        assert data["orderingFields"] == [
            "createdAt",
            "isPinned",
            "lastSeen",
            "roles",
            "status",
            "email",
            "firstName",
            "lastName",
        ]
        assert data["result"][0]["email"] == lucy.email_encrypted
        assert data["result"][1]["email"] == tom.email_encrypted

        # test search
        search_params = {
            str(lucy.id): [
                "lucy",
                "gabe",
            ],
        }
        for id_, params in search_params.items():
            for val in params:
                response = await client.get(
                    self.workspace_managers_url.format(owner_id=tom.id),
                    dict(
                        search=val,
                    ),
                )

                assert response.status_code == 200
                data = response.json()
                assert set(data.keys()) == {"count", "result", "orderingFields"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                assert result[0]["id"] == id_

    async def test_get_workspace_applet_managers_with_pending_invitation(
        self, client, tom, applet_one, applet_one_manager_has_pending_invitation
    ):
        client.login(tom)
        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )

        assert response.status_code == 200
        data = response.json()
        result = data["result"]
        assert data["count"] == 4
        assert len(result) == 4

        approved = [u for u in result if u["status"] == "approved"]
        pending = [u for u in result if u["status"] == "pending"]
        assert len(approved) == 1
        assert len(pending) == 3

    async def test_get_workspace_applet_managers(self, client, tom, lucy, mike, applet_one):
        client.login(tom)
        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )

        assert response.status_code == 200
        assert response.json()["count"] == 3

        plain_emails = [lucy.email_encrypted, tom.email_encrypted, mike.email_encrypted]

        for result in response.json()["result"]:
            assert result["email"] in plain_emails

        # test search
        search_params = {
            str(tom.id): [
                "tom",
                "isaak",
            ],
        }
        for id_, params in search_params.items():
            for val in params:
                response = await client.get(
                    self.workspace_applet_managers_list.format(
                        owner_id=tom.id,
                        applet_id=str(applet_one.id),
                    ),
                    dict(
                        search=val,
                    ),
                )

                assert response.status_code == 200
                data = response.json()
                assert set(data.keys()) == {"count", "result", "orderingFields"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                assert result[0]["id"] == id_
                assert result[0]["firstName"] == tom.first_name
                assert result[0]["lastName"] == tom.last_name
                assert result[0]["email"] == tom.email_encrypted

    async def test_set_workspace_manager_accesses(
        self, client, tom, lucy, applet_one, applet_two, tom_applet_one_subject
    ):
        subject_id = tom_applet_one_subject.id
        client.login(tom)
        response = await client.post(
            self.workspace_manager_accesses_url.format(
                owner_id=tom.id,
                manager_id=lucy.id,
            ),
            dict(
                accesses=[
                    {
                        "applet_id": str(applet_two.id),
                        "roles": ["manager", "coordinator"],
                    },
                    {
                        "applet_id": str(applet_one.id),
                        "roles": ["coordinator", "editor", "reviewer"],
                        "subjects": [
                            str(subject_id),
                        ],
                    },
                ]
            ),
        )

        assert response.status_code == 200, response.json()
        # TODO: check from database results

    async def test_pin_workspace_respondents(self, client, tom, applet_one, applet_one_lucy_respondent):
        client.login(tom)
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )

        assert response.status_code == 200

        user_id = response.json()["result"][-1]["id"]

        # Pin access wrong owner
        response = await client.post(
            self.workspace_respondents_pin.format(owner_id=uuid.uuid4(), user_id=user_id),
        )

        assert response.status_code == 404

        # Pin access wrong access_id
        response = await client.post(
            self.workspace_respondents_pin.format(
                owner_id=tom.id,
                user_id=uuid.uuid4(),
            ),
        )

        assert response.status_code == 403

        # Pin access
        response = await client.post(
            self.workspace_respondents_pin.format(
                owner_id=tom.id,
                user_id=user_id,
            ),
        )

        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )
        assert response.json()["result"][0]["id"] == user_id
        assert response.json()["result"][0]["isPinned"] is True
        assert response.json()["result"][1]["isPinned"] is False

        # Unpin access
        response = await client.post(
            self.workspace_respondents_pin.format(
                owner_id=tom.id,
                user_id=user_id,
            ),
        )

        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )
        assert response.json()["result"][-1]["id"] == user_id

    async def test_pin_workspace_managers(self, client, tom, applet_one, applet_one_lucy_manager):
        client.login(tom)
        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()

        approved = [u for u in data["result"] if u["status"] == "approved"]
        user_id = approved[-1]["id"]

        # Pin access wrong owner
        response = await client.post(
            self.workspace_managers_pin.format(owner_id=uuid.uuid4(), user_id=user_id),
        )

        assert response.status_code == 404

        # Pin access wrong access_id
        response = await client.post(
            self.workspace_managers_pin.format(
                owner_id=tom.id,
                user_id=uuid.uuid4(),
            ),
        )

        assert response.status_code == 403

        # Pin access
        response = await client.post(
            self.workspace_managers_pin.format(
                owner_id=tom.id,
                user_id=user_id,
            ),
        )

        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )
        assert response.json()["result"][0]["id"] == user_id
        assert response.json()["result"][0]["isPinned"] is True
        assert response.json()["result"][1]["isPinned"] is False

        # Unpin access
        response = await client.post(
            self.workspace_managers_pin.format(
                owner_id=tom.id,
                user_id=user_id,
            ),
        )

        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )
        data = response.json()
        approved = [u for u in data["result"] if u["status"] == "approved"]
        assert approved[-1]["id"] == user_id

    async def test_workspace_remove_manager_access(self, client, tom, lucy, applet_one, applet_one_lucy_manager):
        client.login(tom)
        response = await client.get(self.workspace_managers_url.format(owner_id=tom.id))

        assert response.status_code == 200

        managers_count = response.json()["count"]

        data = {
            "user_id": lucy.id,
            "applet_ids": [
                str(applet_one.id),
            ],
            # "role": Role.MANAGER,
        }

        response = await client.delete(self.remove_manager_access, data=data)

        assert response.status_code == 200

        response = await client.get(self.workspace_managers_url.format(owner_id=tom.id))

        assert response.status_code == 200
        assert response.json()["count"] == managers_count - 1

    async def test_folder_applets(self, client, tom):
        client.login(tom)

        response = await client.get(
            self.workspace_folder_applets_url.format(
                owner_id=tom.id,
                folder_id="ecf66358-a717-41a7-8027-807374307732",
            )
        )
        assert response.status_code == 200
        assert response.json()["result"][0]["displayName"] == "Applet 1"
        assert response.json()["result"][1]["displayName"] == "Applet 2"

    async def test_folder_applets_not_super_admin(self, client, bob):
        client.login(bob)

        response = await client.get(
            self.workspace_folder_applets_url.format(
                owner_id=bob.id,
                folder_id="ecf66358-a717-41a7-8027-807374307737",
            )
        )
        assert response.status_code == 200
        assert len(response.json()["result"]) == 1
        assert response.json()["result"][0]["displayName"] == "Applet 4"

    async def test_applets_with_description(self, client, tom, applet_not_in_folder):
        client.login(tom)

        response = await client.get(
            self.workspace_applets_url.format(
                owner_id=tom.id,
            )
        )
        assert response.status_code == 200
        applets = response.json()["result"]
        applet_one = next(i for i in applets if i["id"] == str(applet_not_in_folder.id))
        assert applet_one["activityCount"] == 1
        assert applet_one["description"] == applet_not_in_folder.description

    async def test_applets_flat_list(self, client, lucy):
        client.login(lucy)
        response = await client.get(
            self.workspace_applets_url.format(owner_id=lucy.id),
            dict(ordering="-displayName,created_at", flatList=True),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["type"] == "applet"

    async def test_applet_get_respondent_success(self, client, tom, applet_one, tom_applet_one_subject: Subject):
        client.login(tom)
        url = self.workspace_get_applet_respondent.format(
            owner_id=tom.id,
            applet_id=str(applet_one.id),
            respondent_id=tom.id,
        )
        res = await client.get(url)
        assert res.status_code == 200
        body = res.json()
        respondent = body.get("result")
        assert respondent["nickname"] == f"{tom.first_name} {tom.last_name}"
        # Secret User id is random uuid, so just check that secretUserId exists
        assert respondent["secretUserId"]
        assert respondent["lastSeen"] is None
        assert uuid.UUID(respondent["subjectId"]) == tom_applet_one_subject.id

    async def test_applet_two_get_respondent_success(self, client, tom, applet_two, tom_applet_two_subject: Subject):
        client.login(tom)
        url = self.workspace_get_applet_respondent.format(
            owner_id=tom.id,
            applet_id=str(applet_two.id),
            respondent_id=tom.id,
        )
        res = await client.get(url)
        assert res.status_code == 200
        body = res.json()
        respondent = body.get("result")
        assert respondent["nickname"] == f"{tom.first_name} {tom.last_name}"
        # Secret User id is random uuid, so just check that secretUserId exists
        assert respondent["secretUserId"]
        assert respondent["lastSeen"] is None
        assert uuid.UUID(respondent["subjectId"]) == tom_applet_two_subject.id

    async def test_applet_get_respondent_not_found(self, client, tom, applet_two):
        client.login(tom)
        url = self.workspace_get_applet_respondent.format(
            owner_id=tom.id,
            applet_id=str(applet_two.id),
            respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa0",
        )
        res = await client.get(url)
        assert res.status_code == 404

    async def test_applet_get_respondent_access_denied_for_respondent_role(self, client, tom, bob, applet_two):
        client.login(bob)
        url = self.workspace_get_applet_respondent.format(
            owner_id=tom.id,
            applet_id=str(applet_two.id),
            respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa0",
        )
        res = await client.get(url)
        assert res.status_code == 403

    async def test_get_managers_priority_roles_not_valid_uuid(self, client, tom, bob):
        client.login(bob)
        response = await client.get(
            self.workspaces_priority_role_url.format(owner_id=tom.id),
            query={"appletIDs": "92917a56"},
        )
        assert response.status_code == 422
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == InvalidAppletIDFilter.message

    async def test_get_managers_priority_roles_user_does_not_have_access_to_the_applet(
        self, client, tom, lucy, applet_one_lucy_manager
    ):
        client.login(lucy)
        response = await client.get(
            self.workspaces_priority_role_url.format(owner_id=tom.id),
            query={"appletIDs": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 403
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AppletAccessDenied.message

    async def test_pin_subject_wrong_owner(self, client, tom):
        client.login(tom)
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )

        assert response.status_code == 200, response.json()
        respondent = response.json()["result"][-1]
        subject_id = respondent["details"][0]["subjectId"]
        response = await client.post(self.workspace_subject_pin.format(owner_id=uuid.uuid4(), subject_id=subject_id))
        assert response.status_code == 404

    async def test_pin_subject_wrong_access_id(self, client, tom):
        client.login(tom)
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )

        assert response.status_code == 200, response.json()
        response = await client.post(
            self.workspace_subject_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                subject_id=uuid.uuid4(),
            ),
        )
        assert response.status_code == 403

    async def test_pin_subject(self, client, tom):
        client.login(tom)
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )

        assert response.status_code == 200, response.json()
        respondent = response.json()["result"][-1]
        subject_id = respondent["details"][0]["subjectId"]
        response = await client.post(
            self.workspace_subject_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                subject_id=subject_id,
            ),
        )
        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )
        respondent_list = response.json()["result"]
        for resp in respondent_list:
            for details in resp["details"]:
                if details["subjectId"] == subject_id:
                    assert resp["isPinned"]
                else:
                    assert not resp["isPinned"]

    async def test_unpin_subjects(self, client, tom):
        client.login(tom)
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )

        assert response.status_code == 200, response.json()
        respondent = response.json()["result"][-1]
        subject_id = respondent["details"][0]["subjectId"]
        # Pin
        response = await client.post(
            self.workspace_subject_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                subject_id=subject_id,
            ),
        )
        assert response.status_code == 204
        # Unpin
        response = await client.post(
            self.workspace_subject_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                subject_id=subject_id,
            ),
        )
        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )
        respondent_list = response.json()["result"]
        for resp in respondent_list:
            assert not resp["isPinned"]

    async def test_respondent_access(
        self, client, tom: User, user: User, session: AsyncSession, tom_applets: list[WorkspaceApplet]
    ):
        client.login(tom)
        url = self.workspace_respondent_applet_accesses.format(owner_id=tom.id, respondent_id=tom.id)
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK

    async def test_workspace_respondent_list_for_cross_invited_users(
        self,
        client,
        session,
        tom: User,
        lucy: User,
        applet_one: AppletFull,
        applet_three: AppletFull,
        applet_one_lucy_respondent,
        applet_one_user_respondent,
        applet_three_tom_respondent,
        applet_three_user_respondent,
    ):
        client.login(tom)
        result = await client.get(self.workspace_respondents_url.format(owner_id=tom.id))
        assert result.status_code == http.HTTPStatus.OK
        assert result.json()["count"] == 3

        client.login(lucy)
        result = await client.get(self.workspace_respondents_url.format(owner_id=lucy.id))
        assert result.status_code == http.HTTPStatus.OK
        assert result.json()["count"] == 3

    async def test_workspace_respondent_list_with_subjects(
        self,
        client,
        session,
        tom: User,
        lucy: User,
        user: User,
        applet_one: AppletFull,
        applet_three: AppletFull,
        applet_one_lucy_respondent,
        applet_one_user_respondent,
        applet_three_tom_respondent,
        applet_three_user_respondent,
        applet_one_shell_account: Subject,
    ):
        client.login(tom)
        result = await client.get(self.workspace_respondents_url.format(owner_id=tom.id))
        assert result.status_code == http.HTTPStatus.OK
        assert result.json()["count"] == 4
        respondents = result.json()["result"]

        full_accounts_actual: list[dict] = list(filter(None, map(lambda r: r["id"], respondents)))
        for full_account_expected in [lucy.id, user.id, tom.id]:
            assert str(full_account_expected) in full_accounts_actual

        shell_accounts_actual = map(lambda r: r["details"][0]["subjectId"], filter(lambda r: not r["id"], respondents))
        assert str(applet_one_shell_account.id) == next(shell_accounts_actual)

    async def test_workspace_respondent_update_with_non_existing_respondent_id(
        self,
        client,
        session,
        tom: User,
        applet_one: AppletFull,
    ):
        respondent_id = uuid.uuid4()
        client.login(tom)
        response = await client.post(
            self.applet_respondent_url.format(
                owner_id=tom.id, applet_id=str(applet_one.id), respondent_id=respondent_id
            ),
            dict(
                nickname="New respondent",
                secret_user_id="f0dd4996-e0eb-461f-b2f8-ba873a674710",
            ),
        )
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_workspace_respondent_status(
        self,
        client,
        tom: User,
        user: User,
        lucy: User,
        applet_one: AppletFull,
        applet_one_lucy_respondent,  # invited
        applet_one_shell_account,  # not invited,
        applet_one_user_respondent,  # another one respondent
        applet_one_shell_has_pending_invitation,  # pending
    ):
        client.login(tom)
        result = await client.get(self.workspace_respondents_url.format(owner_id=tom.id))
        assert result.status_code == http.HTTPStatus.OK
        payload = result.json()["result"]
        assert payload
        assert result.json()["count"] == 5
        lucy_respondent = next(filter(lambda x: x["id"] == str(lucy.id), payload))
        tom_respondent = next(filter(lambda x: x["id"] == str(tom.id), payload))
        shell_account_not_invited = next(
            filter(lambda x: x["details"][0]["subjectId"] == str(applet_one_shell_account.id), payload)
        )
        shell_account_pending = next(
            filter(lambda x: x["details"][0]["subjectId"] == str(applet_one_shell_has_pending_invitation.id), payload)
        )
        assert lucy_respondent["status"] == SubjectStatus.INVITED
        assert tom_respondent["status"] == SubjectStatus.INVITED
        assert shell_account_pending["status"] == SubjectStatus.PENDING
        assert shell_account_not_invited["status"] == SubjectStatus.NOT_INVITED

    async def test_workspace_respondent_emails(
        self,
        client,
        tom: User,
        user: User,
        lucy: User,
        applet_one: AppletFull,
        applet_one_lucy_respondent,
        applet_one_shell_account,
        applet_one_user_respondent,
    ):
        client.login(tom)
        result = await client.get(self.workspace_respondents_url.format(owner_id=tom.id))
        assert result.status_code == http.HTTPStatus.OK
        payload = result.json()["result"]
        assert payload
        for respondent in payload:
            assert bool(respondent.get("email"))

    async def test_user_last_activity_workspace_respondent_retrieve(
        self, client, tom: User, applet_one: AppletFull, tom_answer_applet_one
    ):
        url = self.workspace_get_applet_respondent.format(
            owner_id=tom.id, applet_id=applet_one.id, respondent_id=tom.id
        )
        client.login(tom)
        response = await client.get(url)
        assert response.status_code == 200, response.json()
        result = response.json()["result"]
        date_answer = datetime.datetime.fromisoformat(result["lastSeen"])
        date_now = datetime.datetime.now(datetime.UTC)
        assert date_now.day == date_answer.day
        assert date_now.month == date_answer.month
        assert date_now.year == date_answer.year
        assert date_now.hour == date_answer.hour
        assert date_now.minute == date_answer.minute

    async def test_applet_owner_can_view_organizers(self, client, tom):
        client.login(tom)
        response = await client.get(
            self.workspace_managers_url.format(owner_id=tom.id),
            dict(ordering="+email"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1  # lucy
        assert data["count"] == len(data["result"])
        tom_result = data["result"][0]
        assert tom_result["id"] == str(tom.id)
        assert tom_result["email"] == tom.email_encrypted

    async def test_coordinator_can_NOT_view_organizers(
        self,
        client,
        applet_one_lucy_coordinator: AppletFull,
        tom,
    ):
        client.login(applet_one_lucy_coordinator)
        response = await client.get(
            self.workspace_managers_url.format(owner_id=tom.id),
            dict(ordering="+email"),
        )
        assert response.status_code == http.HTTPStatus.UNAUTHORIZED

    async def test_editor_can_NOT_view_organizers(
        self,
        client,
        lucy,
        tom,
        applet_one_lucy_editor: AppletFull,
    ):
        client.login(applet_one_lucy_editor)
        response = await client.get(
            self.workspace_managers_url.format(owner_id=tom.id),
            dict(ordering="+email"),
        )
        assert response.status_code == http.HTTPStatus.UNAUTHORIZED
