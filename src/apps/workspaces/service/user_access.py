import uuid

from apps.answers.crud import AnswerActivityItemsCRUD, AnswerFlowItemsCRUD
from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import UserAppletAccess
from apps.applets.domain.applet import AppletInfo
from apps.shared.query_params import QueryParams
from apps.themes.service import ThemeService
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

    async def get_workspace_applets_by_language(
        self, language: str, query_params: QueryParams
    ) -> list[AppletInfo]:
        """Returns the user their chosen workspace applets."""

        schemas = await UserAppletAccessCRUD().get_accessible_applets(
            self._user_id, query_params
        )

        theme_ids = [schema.theme_id for schema in schemas if schema.theme_id]
        themes = []
        if theme_ids:
            themes = await ThemeService(self._user_id).get_by_ids(theme_ids)

        theme_map = dict((theme.id, theme) for theme in themes)
        applets = []
        for schema in schemas:
            theme = theme_map.get(schema.theme_id)
            applets.append(
                AppletInfo(
                    id=schema.id,
                    display_name=schema.display_name,
                    version=schema.version,
                    description=self._get_by_language(
                        schema.description, language
                    ),
                    theme=theme.dict() if theme else None,
                    about=self._get_by_language(schema.about, language),
                    image=schema.image,
                    watermark=schema.watermark,
                    theme_id=schema.theme_id,
                    report_server_ip=schema.report_server_ip,
                    report_public_key=schema.report_public_key,
                    report_recipients=schema.report_recipients,
                    report_include_user_id=schema.report_include_user_id,
                    report_include_case_id=schema.report_include_case_id,
                    report_email_body=schema.report_email_body,
                    created_at=schema.created_at,
                    updated_at=schema.updated_at,
                )
            )
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

    async def get_workspace_applets_count(
        self, query_params: QueryParams
    ) -> int:
        count = await UserAppletAccessCRUD().get_accessible_applets_count(
            self._user_id, query_params
        )
        return count

    @staticmethod
    def _get_by_language(values: dict, language: str):
        """
        Returns value by language key,
         if it does not exist,
         returns first existing or empty string
        """
        try:
            return values[language]
        except KeyError:
            for key, val in values.items():
                return val
            return ""
