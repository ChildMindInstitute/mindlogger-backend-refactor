import uuid
from collections import defaultdict

from apps.answers.crud import AnswerActivityItemsCRUD, AnswerFlowItemsCRUD
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain.applet import AppletSingleLanguageInfo
from apps.folders.crud import FolderCRUD
from apps.shared.query_params import QueryParams
from apps.themes.service import ThemeService
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role, UserPinRole
from apps.workspaces.domain.user_applet_access import (
    ManagerAccesses,
    ManagerAppletAccess,
    PublicRespondentAppletAccess,
    RemoveManagerAccess,
    RemoveRespondentAccess,
)
from apps.workspaces.domain.workspace import UserWorkspace
from apps.workspaces.errors import (
    AccessDeniedToUpdateOwnAccesses,
    AppletAccessDenied,
    RemoveOwnPermissionAccessDenied,
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

        accesses = await UserAppletAccessCRUD(
            self.session
        ).get_by_user_id_for_managers(self._user_id)

        user_ids = [access.owner_id for access in accesses]
        user_ids.append(self._user_id)

        workspaces = await UserWorkspaceCRUD(self.session).get_by_ids(user_ids)
        return [UserWorkspace.from_orm(workspace) for workspace in workspaces]

    async def get_workspace_applets_by_language(
        self, language: str, query_params: QueryParams
    ) -> list[AppletSingleLanguageInfo]:
        """Returns the user their chosen workspace applets."""
        folder_id = query_params.filters.pop("folder_id", None)
        folder_applet_query = FolderCRUD(self.session).get_folder_applets(
            folder_id, self._user_id
        )

        schemas = await UserAppletAccessCRUD(
            self.session
        ).get_accessible_applets(
            self._user_id, query_params, folder_applet_query, folder_id
        )

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
                    encryption=schema.encryption,
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
                    retention_period=schema.retention_period,
                    retention_type=schema.retention_type,
                )
            )
        return applets

    async def remove_manager_access(self, schema: RemoveManagerAccess):
        """Remove manager access from a specific user."""
        # check if user is owner of all applets
        await self._validate_ownership(schema.applet_ids)
        if self._user_id == schema.user_id:
            raise RemoveOwnPermissionAccessDenied()

        # check if schema.user_id is manager of all applets
        await self._validate_access(
            user_id=schema.user_id,
            removing_applets=schema.applet_ids,
            roles=[schema.role],
            invitor_id=self._user_id,
        )

        # remove manager access
        await UserAppletAccessCRUD(
            self.session
        ).remove_access_by_user_and_applet_to_role(
            schema.user_id, schema.applet_ids, [schema.role]
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
        await UserAppletAccessCRUD(
            self.session
        ).remove_access_by_user_and_applet_to_role(
            schema.user_id, schema.applet_ids, [Role.RESPONDENT]
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
        accesses = await UserAppletAccessCRUD(
            self.session
        ).get_user_applet_accesses_by_roles(
            self._user_id, applet_ids, [Role.OWNER, Role.MANAGER]
        )
        owners_applet_ids = [access.applet_id for access in accesses]
        no_access_applets = set(applet_ids) - set(owners_applet_ids)
        if no_access_applets:
            raise AppletAccessDenied()

    async def _validate_access(
        self,
        user_id: uuid.UUID,
        removing_applets: list[uuid.UUID],
        roles: list[Role],
        invitor_id: uuid.UUID | None = None,
    ):
        accesses = await UserAppletAccessCRUD(
            self.session
        ).get_user_applet_accesses_by_roles(
            user_id, removing_applets, roles, invitor_id
        )
        applet_ids = [access.applet_id for access in accesses]

        no_access_applet = set(removing_applets) - set(applet_ids)
        if no_access_applet:
            raise AppletAccessDenied(
                message=f"User is not related to applets {no_access_applet}"
            )

    async def get_workspace_applets_count(
        self, query_params: QueryParams
    ) -> int:
        folder_id = query_params.filters.pop("folder_id", None)
        folder_applet_query = FolderCRUD(self.session).get_folder_applets(
            folder_id, self._user_id
        )

        count = await UserAppletAccessCRUD(
            self.session
        ).get_accessible_applets_count(
            self._user_id, query_params, folder_applet_query, folder_id
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

    async def check_access(
        self, owner_id: uuid.UUID, roles: list[Role] | None = None
    ):
        # TODO: remove
        if owner_id == self._user_id:
            return

        has_access = await UserAppletAccessCRUD(
            self.session
        ).check_access_by_user_and_owner(self._user_id, owner_id, roles)
        if not has_access:
            raise WorkspaceDoesNotExistError

    async def pin(
        self, owner_id: uuid.UUID, user_id: uuid.UUID, pin_role: UserPinRole
    ):
        await self._validate_pin(owner_id, user_id, pin_role)
        await UserAppletAccessCRUD(self.session).pin(
            self._user_id, owner_id, user_id, pin_role
        )

    async def _validate_pin(
        self, owner_id: uuid.UUID, user_id: uuid.UUID, pin_role: UserPinRole
    ):
        can_pin = await UserAppletAccessCRUD(
            self.session
        ).check_access_by_user_and_owner(
            self._user_id,
            owner_id,
            [Role.MANAGER, Role.COORDINATOR, Role.OWNER],
        )
        if not can_pin:
            raise WorkspaceDoesNotExistError

        roles = None
        if pin_role == UserPinRole.respondent:
            roles = [Role.RESPONDENT]
        elif pin_role == UserPinRole.manager:
            roles = [Role.OWNER, Role.MANAGER, Role.COORDINATOR, Role.EDITOR]

        has_user = await UserAppletAccessCRUD(
            self.session
        ).check_access_by_user_and_owner(user_id, owner_id, roles)
        if not has_user:
            raise UserAppletAccessesDenied

    async def get_respondent_accesses_by_workspace(
        self,
        owner_id: uuid.UUID,
        respondent_id: uuid.UUID,
        query_params: QueryParams,
    ) -> list[PublicRespondentAppletAccess]:
        accesses = await UserAppletAccessCRUD(
            self.session
        ).get_respondent_accesses_by_owner_id(
            owner_id, respondent_id, query_params.page, query_params.limit
        )

        return [
            PublicRespondentAppletAccess.from_orm(access)
            for access in accesses
        ]

    async def get_respondent_accesses_by_workspace_count(
        self,
        owner_id: uuid.UUID,
        respondent_id: uuid.UUID,
    ) -> int:
        count = await UserAppletAccessCRUD(
            self.session
        ).get_respondent_accesses_by_owner_id_count(owner_id, respondent_id)

        return count

    async def get_applets_roles_by_priority(
        self, applet_ids: list[uuid.UUID]
    ) -> dict:
        applet_role_map = await UserAppletAccessCRUD(
            self.session
        ).get_applets_roles_by_priority(applet_ids, self._user_id)

        return applet_role_map

    async def get_manager_accesses(
        self, owner_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[ManagerAppletAccess]:
        accesses = await UserAppletAccessCRUD(
            self.session
        ).get_accesses_by_user_id_in_workspace(
            user_id, owner_id, Role.managers()
        )

        applet_ids = set()
        applet_id_role_map = defaultdict(list)

        for access in accesses:
            applet_ids.add(access.applet_id)
            applet_id_role_map[access.applet_id].append(access.role)

        applets = await AppletsCRUD(self.session).get_by_ids(applet_ids)
        applet_accesses = []

        for applet in applets:
            applet_accesses.append(
                ManagerAppletAccess(
                    applet_id=applet.id,
                    applet_name=applet.display_name,
                    applet_image=applet.image,
                    roles=applet_id_role_map[applet.id],
                )
            )

        return applet_accesses

    async def set(
        self,
        owner_id: uuid.UUID,
        manager_id: uuid.UUID,
        access_data: ManagerAccesses,
    ):
        if manager_id == self._user_id:
            raise AccessDeniedToUpdateOwnAccesses()
        schemas = []
        for access in access_data.accesses:
            try:
                access.roles.remove(Role.OWNER)
            except ValueError:
                pass
            try:
                access.roles.remove(Role.RESPONDENT)
            except ValueError:
                pass
            if Role.MANAGER in access.roles:
                schemas.append(
                    UserAppletAccessSchema(
                        user_id=manager_id,
                        role=Role.MANAGER,
                        applet_id=access.applet_id,
                        owner_id=owner_id,
                        invitor_id=self._user_id,
                    )
                )
            else:
                for role in access.roles:
                    schemas.append(
                        UserAppletAccessSchema(
                            user_id=manager_id,
                            role=role,
                            applet_id=access.applet_id,
                            owner_id=owner_id,
                            invitor_id=self._user_id,
                        )
                    )

        await UserAppletAccessCRUD(
            self.session
        ).remove_manager_accesses_by_user_id_in_workspace(owner_id, manager_id)

        await UserAppletAccessCRUD(self.session).create_many(schemas)
