import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.service.applet import AppletService
from apps.shared.enums import Language
from apps.shared.test import BaseTest
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.workspaces.errors import AppletAccessDenied, InvalidAppletIDFilter
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from config import settings


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
async def applet_one_user_respondent(session: AsyncSession, applet_one: AppletFull, tom, user) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(user.id, Role.RESPONDENT)
    return applet_one


@pytest.fixture
async def applet_one_lucy_roles(
    applet_one_lucy_respondent: AppletFull, applet_one_lucy_coordinator: AppletFull, applet_one_lucy_editor: AppletFull
) -> list[AppletFull]:
    return [applet_one_lucy_respondent, applet_one_lucy_coordinator, applet_one_lucy_editor]


class TestWorkspaces(BaseTest):
    fixtures = [
        "folders/fixtures/folders.json",
        "invitations/fixtures/invitations.json",
        "workspaces/fixtures/workspaces.json",
        "schedule/fixtures/periodicity.json",
        "schedule/fixtures/events.json",
        "schedule/fixtures/activity_events.json",
        "schedule/fixtures/flow_events.json",
        "schedule/fixtures/user_events.json",
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
    workspace_managers_pin = "/workspaces/{owner_id}/managers/{user_id}/pin"
    workspace_get_applet_respondent = "/workspaces/{owner_id}" "/applets/{applet_id}" "/respondents/{respondent_id}"

    @pytest.mark.usefixtures("applet_three")
    async def test_user_workspace_list(self, client, lucy):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

        response = await client.get(self.workspaces_list_url)
        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 1

    async def test_user_workspace_list_super_admin(self, client):
        await client.login(self.login_url, settings.super_admin.email, settings.super_admin.password)

        response = await client.get(self.workspaces_list_url)
        assert response.status_code == 200, response.json()
        # TODO replace 3 with count from database or similar
        # 1 - superadmin and 2 from json fixtures
        assert len(response.json()["result"]) == 3

    async def test_user_workspace_retrieve_without_managers(self, client, lucy):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

        response = await client.get(self.workspaces_detail_url.format(owner_id=lucy.id))
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == "Lucy Gabel Test"
        assert response.json()["result"]["hasManagers"] is False

    async def test_get_users_priority_role_in_workspace(self, client, tom, lucy, applet_one_lucy_coordinator):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

        response = await client.get(self.workspaces_priority_role_url.format(owner_id=tom.id))
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["role"] == Role.COORDINATOR

    async def test_get_users_priority_role_in_workspace_super_admin(self, client, tom):
        await client.login(self.login_url, settings.super_admin.email, settings.super_admin.password)

        response = await client.get(self.workspaces_priority_role_url.format(owner_id=tom.id))
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["role"] == Role.SUPER_ADMIN

    async def test_workspace_roles_retrieve(
        self, client, tom, lucy, applet_one_lucy_respondent, applet_one_lucy_manager, applet_one
    ):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

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
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(self.workspace_roles_url.format(owner_id=tom.id))
        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        roles = data.get(str(applet_one.id), [])
        assert roles == [Role.OWNER, Role.SUPER_ADMIN, Role.RESPONDENT]

    async def test_user_workspace_retrieve_with_managers(self, client, tom, applet_one_lucy_manager):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(self.workspaces_detail_url.format(owner_id=tom.id))
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == "Tom Isaak Test"
        assert response.json()["result"]["hasManagers"] is True

    async def test_user_workspace_retrieve_without_access(self, client, tom, lucy):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(self.workspaces_detail_url.format(owner_id=lucy.id))
        assert response.status_code == 403, response.json()

    async def test_workspace_applets_list(self, client, lucy):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

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
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

        response = await client.get(self.search_workspace_applets_url.format(owner_id=lucy.id, text="applet"))
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["displayName"] == "Applet 3"
        assert response.json()["result"][0]["role"] == Role.OWNER

    async def test_workspace_applets_list_by_folder_id_filter(self, client, tom, applet_not_in_folder):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(
            self.workspace_applets_url.format(owner_id=tom.id),
        )
        assert response.status_code == 200
        # Why 1 applet not in folder and 3 folders
        expected_count = 4
        assert response.json()["count"] == expected_count
        assert len(response.json()["result"]) == expected_count

    async def test_workspace_applets_detail(self, client, lucy, applet_one_lucy_manager):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

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
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

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
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

        response = await client.get(self.workspace_applets_url.format(owner_id="00000000-0000-0000-0000-000000000000"))
        assert response.status_code == 404

    async def test_get_workspace_respondents(self, client, tom, applet_one_lucy_respondent):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.get(
            self.workspace_respondents_url.format(owner_id=tom.id),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["result"][0]["nicknames"]
        assert data["result"][0]["secretIds"]

        # test search
        access_id_0 = data["result"][0]["details"][0]["accessId"]
        access_id_1 = data["result"][1]["details"][0]["accessId"]
        secret_user_id_0 = data["result"][0]["secretIds"][0]
        secret_user_id_1 = data["result"][1]["secretIds"][0]
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
                assert set(data.keys()) == {"count", "result"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                access_ids = {detail["accessId"] for detail in result[0]["details"]}
                assert access_id in access_ids

    async def test_get_workspace_applet_respondents(self, client, tom, applet_one, uuid_zero):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["count"] == 1
        assert data["result"][0]["nicknames"]
        assert data["result"][0]["secretIds"]

        # test search
        access_id = data["result"][0]["details"][0]["accessId"]
        secret_id = data["result"][0]["secretIds"][0]
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

    async def test_get_workspace_respondent_accesses(self, client, tom, lucy, applet_one_lucy_respondent):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.get(
            self.workspace_respondent_applet_accesses.format(
                owner_id=tom.id,
                respondent_id=lucy.id,
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1

    async def test_get_workspace_managers(self, client, tom, lucy, applet_one_lucy_manager):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.get(
            self.workspace_managers_url.format(owner_id=tom.id),
        )

        assert response.status_code == 200
        assert response.json()["count"] == 2

        plain_emails = [tom.email_encrypted, lucy.email_encrypted]

        for result in response.json()["result"]:
            assert result["email"] in plain_emails

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
                assert set(data.keys()) == {"count", "result"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                assert result[0]["id"] == id_

    async def test_get_workspace_applet_managers(self, client, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1

        plain_emails = [tom.email_encrypted]

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
                assert set(data.keys()) == {"count", "result"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                assert result[0]["id"] == id_
                assert result[0]["firstName"] == tom.first_name
                assert result[0]["lastName"] == tom.last_name
                assert result[0]["email"] == tom.email_encrypted

    async def test_set_workspace_manager_accesses(self, client, tom, lucy, applet_one, applet_two):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
                        "respondents": [tom.id],
                    },
                ]
            ),
        )

        assert response.status_code == 200, response.json()
        # TODO: check from database results

    async def test_pin_workspace_respondents(self, client, tom, applet_one, applet_one_lucy_respondent):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id=tom.id,
                applet_id=str(applet_one.id),
            ),
        )

        assert response.status_code == 200, response.json()

        user_id = response.json()["result"][-1]["id"]

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
        assert response.json()["result"][-1]["id"] == user_id

    async def test_workspace_remove_manager_access(self, client, tom, lucy, applet_one, applet_one_lucy_manager):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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

    async def test_workspace_remove_respondent_access(self, client, tom, lucy, applet_one, applet_one_lucy_respondent):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = {
            "user_id": lucy.id,
            "applet_ids": [
                str(applet_one.id),
            ],
            "delete_responses": True,
        }

        response = await client.delete(self.remove_respondent_access, data=data)
        assert response.status_code == 200

    @pytest.mark.usefixtures("applet_one_lucy_coordinator", "applet_one_user_respondent")
    async def test_workspace_coordinator_remove_respondent_access(self, client, lucy, applet_one, user):
        # coordinator can remove respondent access
        await client.login(self.login_url, lucy.email_encrypted, "Test123")

        data = {
            "user_id": user.id,
            "applet_ids": [
                str(applet_one.id),
            ],
            "delete_responses": True,
        }

        response = await client.delete(self.remove_respondent_access, data=data)
        assert response.status_code == 200

    async def test_workspace_editor_remove_respondent_access_error(self, client, session, mike, lucy, applet_one):
        applet_id = str(applet_one.id)
        roles_to_delete = [Role.OWNER, Role.COORDINATOR, Role.MANAGER, Role.SUPER_ADMIN, Role.REVIEWER]
        await UserAppletAccessCRUD(session).delete_user_roles(uuid.UUID(applet_id), mike.id, roles_to_delete)
        # editor can remove respondent access
        await client.login(self.login_url, mike.email_encrypted, "Test1234")

        data = {
            "user_id": lucy.id,
            "applet_ids": [applet_id],
            "delete_responses": True,
        }

        response = await client.delete(self.remove_respondent_access, data=data)
        assert response.status_code == 403

    async def test_folder_applets(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

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
        await client.login(self.login_url, bob.email_encrypted, "Test1234!")

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
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

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
        await client.login(self.login_url, lucy.email_encrypted, "Test123")
        response = await client.get(
            self.workspace_applets_url.format(owner_id=lucy.id),
            dict(ordering="-displayName,created_at", flatList=True),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["type"] == "applet"

    async def test_applet_get_respondent_success(self, client, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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

    async def test_applet_get_respondent_not_found(self, client, tom, applet_two):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        url = self.workspace_get_applet_respondent.format(
            owner_id=tom.id,
            applet_id=str(applet_two.id),
            respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa0",
        )
        res = await client.get(url)
        assert res.status_code == 404

    async def test_applet_get_respondent_access_denied_for_respondent_role(self, client, tom, bob, applet_two):
        await client.login(self.login_url, bob.email_encrypted, "Test1234!")
        url = self.workspace_get_applet_respondent.format(
            owner_id=tom.id,
            applet_id=str(applet_two.id),
            respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa0",
        )
        res = await client.get(url)
        assert res.status_code == 403

    async def test_get_managers_priority_roles_not_valid_uuid(self, client, tom, bob):
        await client.login(self.login_url, bob.email_encrypted, "Test1234!")
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
        await client.login(self.login_url, lucy.email_encrypted, "Test123")
        response = await client.get(
            self.workspaces_priority_role_url.format(owner_id=tom.id),
            query={"appletIDs": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 403
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AppletAccessDenied.message
