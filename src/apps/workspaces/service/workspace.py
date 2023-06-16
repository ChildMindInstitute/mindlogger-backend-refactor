import uuid
from typing import Tuple

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
        return WorkspaceInfo(
            name=schema.workspace_name, has_managers=has_managers
        )

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
        users, total = await UserAppletAccessCRUD(
            self.session
        ).get_workspace_managers(
            self._user_id, owner_id, applet_id, query_params
        )

        return users, total

    async def get_workspace_applets(
        self,
        language: str,
        query_params: QueryParams,
        roles: list[Role] | None = None,
    ) -> list[WorkspaceApplet]:
        applets = await UserAccessService(
            self.session, self._user_id
        ).get_workspace_applets_by_language(language, query_params, roles)

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
