import uuid
from typing import Tuple

from apps.applets.crud import AppletsCRUD
from apps.shared.encryption import decrypt
from apps.shared.query_params import QueryParams
from apps.users import User, UsersCRUD
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.db.schemas import UserWorkspaceSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.workspace import (
    WorkspaceApplet,
    WorkspaceInfo,
    WorkspaceManager,
    WorkspaceRespondent,
    WorkspaceSearchApplet,
)
from apps.workspaces.errors import (
    InvalidAppletIDFilter,
    WorkspaceAccessDenied,
    WorkspaceDoesNotExistError,
)
from apps.workspaces.service.check_access import CheckAccessService
from apps.workspaces.service.user_access import UserAccessService


class WorkspaceService:
    def __init__(self, session, user_id: uuid.UUID):
        self._user_id = user_id
        self.session = session

    async def create_workspace_from_user(
        self, user: User
    ) -> UserWorkspaceSchema:
        schema = await UserWorkspaceCRUD(self.session).save(
            UserWorkspaceSchema(
                user_id=user.id,
                workspace_name=f"{user.first_name} {user.last_name}",
                is_modified=False,
            )
        )
        return schema

    async def get_workspace(self, user_id: uuid.UUID) -> WorkspaceInfo:
        await self.has_access(
            user_id,
            self._user_id,
            [
                Role.OWNER,
                Role.MANAGER,
                Role.COORDINATOR,
                Role.EDITOR,
                Role.REVIEWER,
            ],
        )
        schema = await UserWorkspaceCRUD(self.session).get_by_user_id(
            self._user_id
        )
        has_managers = await UserAppletAccessCRUD(self.session).has_managers(
            self._user_id
        )
        workspace_name = decrypt(schema.workspace_name).decode("utf-8")
        return WorkspaceInfo(name=workspace_name, has_managers=has_managers)

    async def has_access(
        self, user_id: uuid.UUID, owner_id: uuid.UUID, roles: list[Role]
    ):
        has_access = await UserAppletAccessCRUD(self.session).has_access(
            user_id, owner_id, roles
        )
        if not has_access:
            raise WorkspaceAccessDenied()

    async def update_workspace_name(
        self, user: User, workspace_prefix: str | None = None
    ):
        """
        Let's check if the workspace name has changed before.
        We don't do anything. Otherwise, accept the workspace prefix value
        and update the workspace name. This procedure is performed only once.
        You can't change the workspace name after that.
        """
        user_workspace = await UserWorkspaceCRUD(self.session).get_by_user_id(
            user.id
        )
        if not user_workspace:
            user_workspace = await self.create_workspace_from_user(user)
        if not user_workspace.is_modified and workspace_prefix:
            await UserWorkspaceCRUD(self.session).update(
                user,
                workspace_prefix,
            )

    async def get_workspace_respondents(
        self,
        owner_id: uuid.UUID,
        applet_id: uuid.UUID | None,
        query_params: QueryParams,
    ) -> Tuple[list[WorkspaceRespondent], int]:
        users, total = await UserAppletAccessCRUD(
            self.session
        ).get_workspace_respondents(
            self._user_id, owner_id, applet_id, query_params
        )

        return users, total

    async def get_workspace_managers(
        self,
        owner_id: uuid.UUID,
        applet_id: uuid.UUID | None,
        query_params: QueryParams,
    ) -> Tuple[list[WorkspaceManager], int]:

        # TODO: Investigate if we do need the search by email
        # hash the email is exist in the search
        # if query_params.search and EMAIL_REGEX.match(query_params.search):
        #     query_params.search = hash_sha224(query_params.search)

        users, total = await UserAppletAccessCRUD(
            self.session
        ).get_workspace_managers(
            self._user_id, owner_id, applet_id, query_params
        )

        return users, total

    async def get_workspace_applets(
        self, owner_id: uuid.UUID, language: str, query_params: QueryParams
    ) -> list[WorkspaceApplet]:
        folder_or_applets = []
        applets_crud = AppletsCRUD(self.session)
        if query_params.filters.get("flat_list"):
            workspace_applets = await applets_crud.get_applets_flat_list(
                owner_id, self._user_id, query_params
            )
        else:
            workspace_applets = await applets_crud.get_workspace_applets(
                owner_id, self._user_id, query_params
            )
        for folder_or_applet in workspace_applets:
            folder_or_applets.append(
                WorkspaceApplet(
                    id=folder_or_applet[0],
                    display_name=folder_or_applet[1],
                    image=folder_or_applet[2],
                    is_pinned=folder_or_applet[3],
                    encryption=folder_or_applet[4],
                    created_at=folder_or_applet[5],
                    updated_at=folder_or_applet[6],
                    version=folder_or_applet[7],
                    type=folder_or_applet[8],
                    role=folder_or_applet[9],
                    folders_applet_count=folder_or_applet[10],
                    description=folder_or_applet[12],
                    activity_count=folder_or_applet[13],
                )
            )
        return folder_or_applets

    async def search_workspace_applets(
        self,
        owner_id: uuid.UUID,
        search_text,
        language: str,
        query_params: QueryParams,
    ) -> list[WorkspaceSearchApplet]:
        folder_or_applets = []
        workspace_applets = await AppletsCRUD(
            self.session
        ).search_workspace_applets(
            owner_id, self._user_id, search_text, query_params
        )
        for folder_or_applet in workspace_applets:
            folder_or_applets.append(
                WorkspaceSearchApplet(
                    id=folder_or_applet[0],
                    display_name=folder_or_applet[1],
                    image=folder_or_applet[2],
                    is_pinned=False,
                    encryption=folder_or_applet[3],
                    created_at=folder_or_applet[4],
                    updated_at=folder_or_applet[5],
                    version=folder_or_applet[6],
                    type="applet",
                    role=folder_or_applet[7],
                    folder_id=folder_or_applet[8],
                    folder_name=folder_or_applet[9],
                )
            )
        return folder_or_applets

    async def search_workspace_applets_count(
        self,
        owner_id: uuid.UUID,
        search_text,
    ) -> int:
        count = await AppletsCRUD(self.session).search_workspace_applets_count(
            owner_id, self._user_id, search_text
        )

        return count

    async def get_workspace_applets_count(
        self, owner_id: uuid.UUID, query: QueryParams
    ) -> int:
        applet_crud = AppletsCRUD(self.session)
        if query.filters["flat_list"]:
            count = await applet_crud.get_workspace_applets_flat_list_count(
                owner_id, self._user_id
            )
        else:
            count = await applet_crud.get_workspace_applets_count(
                owner_id, self._user_id
            )
        return count

    async def get_workspace_folder_applets(
        self, owner_id: uuid.UUID, folder_id: uuid.UUID, language: str
    ) -> list[WorkspaceApplet]:
        schemas = await AppletsCRUD(self.session).get_folders_applets(
            owner_id, self._user_id, folder_id
        )

        applets = []
        for schema, is_pinned in schemas:
            applets.append(
                WorkspaceApplet(
                    id=schema.id,
                    display_name=schema.display_name,
                    image=schema.image,
                    is_pinned=is_pinned,
                    encryption=schema.encryption,
                    created_at=schema.created_at,
                    updated_at=schema.updated_at,
                    version=schema.version,
                    type="applet",
                    folders_applet_count=0,
                )
            )

        applet_ids = [applet.id for applet in applets]

        workspace_applets = []
        workspace_applet_map = dict()
        for applet in applets:
            workspace_applet = WorkspaceApplet.from_orm(applet)
            workspace_applet_map[workspace_applet.id] = workspace_applet
            workspace_applets.append(workspace_applet)

        applet_role_map = await UserAccessService(
            self.session, self._user_id
        ).get_applets_roles_by_priority(applet_ids)

        for applet_id, role in applet_role_map.items():
            workspace_applet_map[applet_id].role = role
        return workspace_applets

    async def exists_by_owner_id(self, owner_id: uuid.UUID):
        exists = await UsersCRUD(self.session).exist_by_key("id", owner_id)
        if not exists:
            raise WorkspaceDoesNotExistError()

    async def get_applets_roles_by_priority(self, owner_id, appletIDs):
        # parse applet ids
        try:
            applet_ids = list(
                map(uuid.UUID, filter(None, appletIDs.split(",")))
            )
        except ValueError:
            raise InvalidAppletIDFilter

        # check if applets exist
        for applet_id in applet_ids:
            await CheckAccessService(
                self.session, self._user_id
            ).check_applet_detail_access(applet_id)

        return await UserAppletAccessCRUD(
            self.session
        ).get_applets_roles_by_priority_for_workspace(
            owner_id, self._user_id, applet_ids
        )
