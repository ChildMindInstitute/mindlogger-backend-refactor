import uuid

from apps.answers.crud import AnswerActivityItemsCRUD, AnswerFlowItemsCRUD
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain import UserAppletAccess
from apps.applets.domain.applet import AppletPublic
from apps.users import User, UsersCRUD
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.user_applet_access import (
    RemoveManagerAccess,
    RemoveRespondentAccess,
)
from apps.workspaces.domain.workspace import PublicWorkspace
from apps.workspaces.errors import AppletAccessDenied

__all__ = ["UserAccessService"]


class UserAccessService:
    def __init__(self, user_id: uuid.UUID):
        self._user_id = user_id

    async def get_user_workspaces(self) -> list[PublicWorkspace]:
        """
        Returns the user their current workspaces.
        Workspaces in which the user is the owner or invited user
        """

        accesses: list[
            UserAppletAccess
        ] = await UserAppletAccessCRUD().get_by_user_id(self._user_id)

        workspaces: list[PublicWorkspace] = []

        for access in accesses:
            user_owner: User = await UsersCRUD().get_by_id(access.owner_id)
            workspace_internal = await UserWorkspaceCRUD().get_by_user_id(
                user_owner.id
            )
            workspace = PublicWorkspace(
                owner_id=access.owner_id,
                workspace_name=workspace_internal.workspace_name,
            )
            if workspace not in workspaces:
                workspaces.append(workspace)

        return workspaces

    # TODO: Finish with paginatination
    async def get_workspace_applets(
        self, owner_id: uuid.UUID
    ) -> list[AppletPublic]:
        """Returns the user their chosen workspace applets."""

        accesses: list[
            UserAppletAccess
        ] = await UserAppletAccessCRUD().get_by_user_id(self._user_id)

        applets: list[AppletPublic] = []

        for access in accesses:
            if access.owner_id == owner_id:
                applet: AppletPublic = await AppletsCRUD().get_by_id(
                    access.applet_id
                )
                if applet not in applets:
                    applets.append(applet)

        return applets

    async def remove_manager_access(self, schema: RemoveManagerAccess):
        """Remove manager access from a specific user."""
        # check if user is owner of all applets
        await self._validate_ownership(schema.applet_ids)

        # check if schema.user_id is manager of all applets
        await self._validate_access(
            user_id=schema.user_id,
            removing_applets=schema.applet_ids,
            roles=[
                Role.MANAGER,
                Role.COORDINATOR,
                Role.EDITOR,
                Role.REVIEWER,
            ],
        )

        # remove manager access
        for applet_id in schema.applet_ids:
            await UserAppletAccessCRUD().delete_all_by_user_and_applet(
                user_id=schema.user_id, applet_id=applet_id
            )

    async def remove_respondent_access(self, schema: RemoveRespondentAccess):
        """Remove respondent access from a specific user."""
        # check if user is owner of all applets
        await self._validate_ownership(schema.applet_ids)

        # check if schema.user_id is respondent of all applets
        await self._validate_access(
            user_id=schema.user_id,
            removing_applets=schema.applet_ids,
            roles=[Role.RESPONDENT],
        )

        # remove respondent access
        for applet_id in schema.applet_ids:
            await UserAppletAccessCRUD().delete_all_by_user_and_applet(
                user_id=schema.user_id, applet_id=applet_id
            )

        # delete all responses of respondent in applets
        if schema.delete_responses:
            for applet_id in schema.applet_ids:
                await AnswerActivityItemsCRUD().delete_by_applet_user(
                    applet_id=applet_id, user_id=schema.user_id
                )
                await AnswerFlowItemsCRUD().delete_by_applet_user(
                    user_id=schema.user_id, applet_id=applet_id
                )

    async def _validate_ownership(self, applet_ids: list[uuid.UUID]):
        owners_applet_ids = [
            owner_applet.applet_id
            for owner_applet in (
                await UserAppletAccessCRUD().get_all_by_user_id_and_roles(
                    self._user_id, roles=[Role.ADMIN]
                )
            )
        ]
        for applet_id in applet_ids:
            if applet_id not in owners_applet_ids:
                raise AppletAccessDenied(
                    message=f"User is not owner of applet {applet_id}"
                )

    async def _validate_access(
        self,
        user_id: uuid.UUID,
        removing_applets: list[uuid.UUID],
        roles: list[Role],
    ):
        # check if user_id has access to applets with roles
        applet_ids = [
            manager_applet.applet_id
            for manager_applet in (
                await UserAppletAccessCRUD().get_all_by_user_id_and_roles(
                    user_id,
                    roles=roles,
                )
            )
        ]

        for applet_id in removing_applets:
            if applet_id not in applet_ids:
                raise AppletAccessDenied(
                    message=f"User is not related to applet {applet_id}"
                )
