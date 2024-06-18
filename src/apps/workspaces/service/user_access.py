import json
import uuid
from gettext import gettext as _

import config
from apps.answers.crud.answers import AnswersCRUD
from apps.applets.crud import UserAppletAccessCRUD
from apps.integrations.domain import Integration
from apps.invitations.domain import ReviewerMeta
from apps.invitations.errors import RespondentsNotSet
from apps.shared.exception import AccessDeniedError, ValidationError
from apps.shared.query_params import QueryParams
from apps.subjects.crud import SubjectsCrud
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role, UserPinRole
from apps.workspaces.domain.user_applet_access import (
    ManagerAccesses,
    PublicRespondentAppletAccess,
    RemoveManagerAccess,
    RemoveRespondentAccess,
)
from apps.workspaces.domain.workspace import UserWorkspace
from apps.workspaces.errors import (
    AccessDeniedToUpdateOwnAccesses,
    AppletAccessDenied,
    RemoveOwnPermissionAccessDenied,
    TransferOwnershipAccessDenied,
    UserAccessAlreadyExists,
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

        accesses = await UserAppletAccessCRUD(self.session).get_by_user_id_for_managers(self._user_id)

        user_ids = [access.owner_id for access in accesses]
        user_ids.append(self._user_id)

        workspaces = await UserWorkspaceCRUD(self.session).get_by_ids(user_ids)
        return [
            UserWorkspace(
                user_id=workspace.user_id,
                workspace_name=workspace.workspace_name,
                integrations=[Integration.parse_obj(integration) for integration in json.loads(workspace.integrations)],
            )
            for workspace in workspaces
        ]

    async def get_super_admin_workspaces(self) -> list[UserWorkspace]:
        """
        Returns the super admins workspaces.
        """

        workspaces = await UserWorkspaceCRUD(self.session).get_all()
        return [
            UserWorkspace(
                user_id=workspace.user_id,
                workspace_name=workspace.workspace_name,
                integrations=[Integration.parse_obj(integration) for integration in json.loads(workspace.integrations)],
            )
            for workspace in workspaces
        ]

    async def remove_manager_access(self, schema: RemoveManagerAccess):
        """Remove manager access from a specific user."""
        # TODO rework logic: query to remove all managers less by rang
        if self._user_id == schema.user_id:
            raise RemoveOwnPermissionAccessDenied()

        manager_roles = [
            Role.COORDINATOR,
            Role.EDITOR,
            Role.REVIEWER,
        ]
        try:
            await self._validate_ownership(schema.applet_ids, [Role.OWNER])
            manager_roles.append(Role.MANAGER)
        except AppletAccessDenied:
            await self._validate_ownership(schema.applet_ids, [Role.MANAGER])

        # check if schema.user_id is manager of all applets
        await self._validate_access(
            user_id=schema.user_id,
            removing_applets=schema.applet_ids,
            roles=manager_roles,
        )
        # remove manager access
        await UserAppletAccessCRUD(self.session).remove_access_by_user_and_applet_to_role(
            schema.user_id, schema.applet_ids, manager_roles
        )

    async def remove_respondent_access(self, schema: RemoveRespondentAccess):
        """Remove respondent access from a specific user."""
        # check if user is owner of all applets
        await self._validate_ownership(schema.applet_ids, [Role.OWNER, Role.MANAGER, Role.COORDINATOR])

        # check if schema.user_id is respondent of all applets
        await self._validate_access(
            user_id=schema.user_id,
            removing_applets=schema.applet_ids,
            roles=[Role.RESPONDENT],
        )

        # remove respondent access
        await UserAppletAccessCRUD(self.session).remove_access_by_user_and_applet_to_role(
            schema.user_id, schema.applet_ids, [Role.RESPONDENT]
        )

        # delete all responses of respondent in applets
        if schema.delete_responses:
            for applet_id in schema.applet_ids:
                await AnswersCRUD(self.session).delete_by_applet_user(
                    applet_id,
                    schema.user_id,
                )

    async def _validate_ownership(self, applet_ids: list[uuid.UUID], roles: list[Role]):
        accesses = await UserAppletAccessCRUD(self.session).get_user_applet_accesses_by_roles(
            self._user_id,
            applet_ids,
            roles,
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
        accesses = await UserAppletAccessCRUD(self.session).get_user_applet_accesses_by_roles(
            user_id, removing_applets, roles, invitor_id
        )
        applet_ids = [access.applet_id for access in accesses]

        no_access_applet = set(removing_applets) - set(applet_ids)
        if no_access_applet:
            raise AppletAccessDenied(message=f"User is not related to applets {no_access_applet}")

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

    async def check_access(self, owner_id: uuid.UUID, roles: list[Role] | None = None):
        # TODO: remove
        if owner_id == self._user_id:
            return

        has_access = await UserAppletAccessCRUD(self.session).check_access_by_user_and_owner(
            self._user_id, owner_id, roles
        )
        if not has_access:
            raise WorkspaceDoesNotExistError

    async def pin(
        self,
        owner_id: uuid.UUID,
        pin_role: UserPinRole,
        user_id: uuid.UUID | None = None,
        subject_id: uuid.UUID | None = None,
    ):
        await self._validate_pin(owner_id, pin_role, user_id, subject_id)
        await UserAppletAccessCRUD(self.session).pin(self._user_id, owner_id, pin_role, user_id, subject_id)

    async def _validate_pin(
        self, owner_id: uuid.UUID, pin_role: UserPinRole, user_id: uuid.UUID | None, subject_id: uuid.UUID | None
    ):
        can_pin = await UserAppletAccessCRUD(self.session).check_access_by_user_and_owner(
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

        access_crud = UserAppletAccessCRUD(self.session)
        if user_id:
            has_user = await access_crud.check_access_by_user_and_owner(user_id, owner_id, roles)
        elif subject_id:
            has_user = await access_crud.check_access_by_subject_and_owner(subject_id, owner_id, roles)
        else:
            raise UserAppletAccessesDenied
        if not has_user:
            raise UserAppletAccessesDenied

    async def get_respondent_accesses_by_workspace(
        self,
        owner_id: uuid.UUID,
        respondent_id: uuid.UUID,
        query_params: QueryParams,
    ) -> list[PublicRespondentAppletAccess]:
        accesses = await UserAppletAccessCRUD(self.session).get_respondent_accesses_by_owner_id(
            owner_id, respondent_id, query_params.page, query_params.limit
        )

        return [PublicRespondentAppletAccess.from_orm(access) for access in accesses]

    async def get_respondent_accesses_by_workspace_count(
        self,
        owner_id: uuid.UUID,
        respondent_id: uuid.UUID,
    ) -> int:
        count = await UserAppletAccessCRUD(self.session).get_respondent_accesses_by_owner_id_count(
            owner_id, respondent_id
        )

        return count

    async def get_applets_roles_by_priority(self, applet_ids: list[uuid.UUID]) -> dict:
        applet_role_map = await UserAppletAccessCRUD(self.session).get_applets_roles_by_priority(
            applet_ids, self._user_id
        )

        return applet_role_map

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
            for role in access.roles:
                if role in [Role.OWNER, Role.SUPER_ADMIN]:
                    raise TransferOwnershipAccessDenied()
            try:
                access.roles.remove(Role.RESPONDENT)
            except ValueError:
                pass
            meta: dict = {}
            if Role.MANAGER in access.roles:
                schemas.append(
                    UserAppletAccessSchema(
                        user_id=manager_id,
                        role=Role.MANAGER,
                        applet_id=access.applet_id,
                        owner_id=owner_id,
                        invitor_id=self._user_id,
                        is_deleted=False,
                        meta=meta,
                    )
                )
            else:
                for role in access.roles:
                    meta = {}
                    if role == Role.REVIEWER:
                        if subject_ids := access.subjects:
                            subject_ids = list(set(subject_ids))
                            existing_subject_ids = await SubjectsCrud(self.session).reduce_applet_subject_ids(
                                access.applet_id, subject_ids
                            )

                            if len(existing_subject_ids) != len(subject_ids):
                                raise ValidationError(_("Subject does not exist in applet"))

                            meta = ReviewerMeta(subjects=list(map(str, subject_ids))).dict()
                        else:
                            raise RespondentsNotSet()
                    schemas.append(
                        UserAppletAccessSchema(
                            user_id=manager_id,
                            role=role,
                            applet_id=access.applet_id,
                            owner_id=owner_id,
                            invitor_id=self._user_id,
                            is_deleted=False,
                            meta=meta,
                        )
                    )

        for schema in schemas:
            user_access = await UserAppletAccessCRUD(self.session).get_by_user_applet_accesses(
                schema.user_id, schema.applet_id, schema.role
            )
            if user_access:
                raise UserAccessAlreadyExists()
            else:
                await UserAppletAccessCRUD(self.session).upsert_user_applet_access(schema)

    async def get_workspace_applet_roles(
        self,
        owner_id: uuid.UUID,
        applet_ids: list[uuid.UUID] | None = None,
        is_super_admin=False,
    ) -> dict[uuid.UUID, list[Role]]:
        applet_roles = await UserAppletAccessCRUD(self.session).get_workspace_applet_roles(
            owner_id, self._user_id, applet_ids
        )
        if is_super_admin:
            for applet_role in applet_roles:
                if Role.OWNER in applet_role.roles:
                    applet_role.roles.insert(1, Role.SUPER_ADMIN)
                else:
                    applet_role.roles.insert(0, Role.SUPER_ADMIN)

        return {val.applet_id: val.roles for val in applet_roles}

    @staticmethod
    def raise_for_developer_access(email: str | None):
        if not email:
            raise AccessDeniedError()
        email_list = config.settings.logs.get_access_emails()
        if email not in email_list:
            raise AccessDeniedError()

    async def get_management_applets(self, applet_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        return await UserAppletAccessCRUD(self.session).get_management_applets(self._user_id, applet_ids)

    async def validate_subject_delete_access(self, applet_id: uuid.UUID):
        await self._validate_ownership([applet_id], [Role.OWNER, Role.MANAGER, Role.COORDINATOR])

    async def change_subject_pins_to_user(self, user_id: uuid.UUID, subject_id: uuid.UUID):
        return await UserAppletAccessCRUD(self.session).change_subject_pins_to_user(user_id, subject_id)
