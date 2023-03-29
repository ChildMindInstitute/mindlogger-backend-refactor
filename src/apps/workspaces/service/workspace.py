import uuid

from apps.shared.query_params import QueryParams
from apps.users import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.db.schemas import UserWorkspaceSchema
from apps.workspaces.domain.workspace import WorkspaceUser


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
        if not user_workspace.is_modified:
            await UserWorkspaceCRUD(self.session).update(
                user,
                workspace_prefix,
            )

    async def get_workspace_users(
        self, owner_id: uuid.UUID, query_params: QueryParams
    ) -> list[WorkspaceUser]:
        users = await UserAppletAccessCRUD(self.session).get_workspace_users(
            owner_id, query_params
        )
        return users

    async def get_workspace_users_count(
        self, owner_id: uuid.UUID, query_params: QueryParams
    ):
        return await UserAppletAccessCRUD(
            self.session
        ).get_workspace_users_count(owner_id, query_params)
