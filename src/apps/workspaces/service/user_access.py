import uuid

from apps.answers.crud import AnswerActivityItemsCRUD, AnswerFlowItemsCRUD
from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain.applet import AppletSingleLanguageInfo
from apps.shared.query_params import QueryParams
from apps.themes.service import ThemeService
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.user_applet_access import (
    RemoveManagerAccess,
    RemoveRespondentAccess,
    RespondentAppletAccess,
)
from apps.workspaces.domain.workspace import UserWorkspace
from apps.workspaces.errors import (
    AppletAccessDenied,
    UserAppletAccessesDenied,
    WorkspaceDoesNotExistError,
)

__all__ = ["UserAccessService"]


class UserAccessService:
    def __init__(self, session, user_id: uuid.UUID):
        self._user_id = user_id
        self.session = session

    async def get_user_workspaces(self) -> list[UserWorkspace]:
        """
        Returns the user their current workspaces.
        Workspaces in which the user is the owner or invited user
        """

        accesses = await UserAppletAccessCRUD(self.session).get_by_user_id(
            self._user_id
        )

        user_ids = [access.owner_id for access in accesses]
        user_ids.append(self._user_id)

        workspaces = await UserWorkspaceCRUD(self.session).get_by_ids(user_ids)
        return [UserWorkspace.from_orm(workspace) for workspace in workspaces]

    async def get_workspace_applets_by_language(
        self, language: str, query_params: QueryParams
    ) -> list[AppletSingleLanguageInfo]:
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
                AppletSingleLanguageInfo(
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
        await UserAppletAccessCRUD(self.session).delete_all_by_user_and_applet(
            schema.user_id, schema.applet_ids
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
        await UserAppletAccessCRUD(self.session).delete_all_by_user_and_applet(
            schema.user_id, schema.applet_ids
        )

        # delete all responses of respondent in applets
        if schema.delete_responses:
            for applet_id in schema.applet_ids:
                await AnswerActivityItemsCRUD(
                    self.session
                ).delete_by_applet_user(
                    applet_id=applet_id, user_id=schema.user_id
                )
                await AnswerFlowItemsCRUD(self.session).delete_by_applet_user(
                    user_id=schema.user_id, applet_id=applet_id
                )

    async def _validate_ownership(self, applet_ids: list[uuid.UUID]):
        owners_applet_ids = [
            owner_applet.applet_id
            for owner_applet in (
                await UserAppletAccessCRUD(
                    self.session
                ).get_all_by_user_id_and_roles(
                    self._user_id, roles=[Role.ADMIN]
                )
            )
        ]
        no_access_applets = set(applet_ids) - set(owners_applet_ids)
        if no_access_applets:
            raise AppletAccessDenied(
                message=f"User is not owner of applets {no_access_applets}"
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
                await UserAppletAccessCRUD(
                    self.session
                ).get_all_by_user_id_and_roles(
                    user_id,
                    roles=roles,
                )
            )
        ]

        no_access_applet = set(removing_applets) - set(applet_ids)
        if no_access_applet:
            raise AppletAccessDenied(
                message=f"User is not related to applets {no_access_applet}"
            )

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

    async def check_access(self, owner_id: uuid.UUID):
        has_access = await UserAppletAccessCRUD(
            self.session
        ).check_access_by_user_and_owner(self._user_id, owner_id)
        if not has_access:
            raise WorkspaceDoesNotExistError

    async def pin(self, access_id: uuid.UUID):
        await self._validate_pin(access_id)
        await UserAppletAccessCRUD(self.session).pin(access_id)

    async def _validate_pin(self, access_id: uuid.UUID):
        access = await UserAppletAccessCRUD(self.session).get_by_id(access_id)
        applet_manager_ids = await UserAppletAccessCRUD(
            self.session
        ).get_applet_users_by_roles(
            access.applet_id, [Role.MANAGER, Role.COORDINATOR, Role.ADMIN]
        )
        if self._user_id not in applet_manager_ids:
            raise UserAppletAccessesDenied

    async def get_respondent_accesses_by_workspace(
        self,
        owner_id: uuid.UUID,
        respondent_id: uuid.UUID,
        query_params: QueryParams,
    ) -> list[RespondentAppletAccess]:
        accesses = await UserAppletAccessCRUD(
            self.session
        ).get_respondent_accesses_by_owner_id(
            owner_id, respondent_id, query_params.page, query_params.limit
        )

        return accesses

    async def get_respondent_accesses_by_workspace_count(
        self,
        owner_id: uuid.UUID,
        respondent_id: uuid.UUID,
    ) -> int:
        count = await UserAppletAccessCRUD(
            self.session
        ).get_respondent_accesses_by_owner_id_count(owner_id, respondent_id)

        return count
