import uuid

from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import UserAppletAccess
from apps.applets.domain.applet import AppletInfo
from apps.shared.query_params import QueryParams
from apps.themes.service import ThemeService
from apps.users import User, UsersCRUD
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.domain.workspace import PublicWorkspace

__all__ = ["UserAccessService"]


class UserAccessService:
    def __init__(self, session, user_id: uuid.UUID):
        self._user_id = user_id
        self.session = session

    async def get_user_workspaces(self) -> list[PublicWorkspace]:
        """
        Returns the user their current workspaces.
        Workspaces in which the user is the owner or invited user
        """

        accesses: list[UserAppletAccess] = await UserAppletAccessCRUD(
            self.session
        ).get_by_user_id(self._user_id)

        workspaces: list[PublicWorkspace] = []

        for access in accesses:
            user_owner: User = await UsersCRUD(self.session).get_by_id(
                access.owner_id
            )
            workspace_internal = await UserWorkspaceCRUD(
                self.session
            ).get_by_user_id(user_owner.id)
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

        schemas = await UserAppletAccessCRUD(
            self.session
        ).get_accessible_applets(self._user_id, query_params)

        theme_ids = [schema.theme_id for schema in schemas if schema.theme_id]
        themes = []
        if theme_ids:
            themes = await ThemeService(
                self.session, self._user_id
            ).get_by_ids(theme_ids)

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

    async def get_workspace_applets_count(
        self, query_params: QueryParams
    ) -> int:
        count = await UserAppletAccessCRUD(
            self.session
        ).get_accessible_applets_count(self._user_id, query_params)
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
