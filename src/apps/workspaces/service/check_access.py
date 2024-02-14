import uuid

from apps.workspaces.crud.applet_access import AppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.errors import (
    AnswerCheckAccessDenied,
    AnswerCreateAccessDenied,
    AnswerNoteCRUDAccessDenied,
    AnswerViewAccessDenied,
    AppletAccessDenied,
    AppletCreationAccessDenied,
    AppletDeleteAccessDenied,
    AppletDuplicateAccessDenied,
    AppletEditionAccessDenied,
    AppletInviteAccessDenied,
    AppletSetScheduleAccessDenied,
    PublishConcealAccessDenied,
    TransferOwnershipAccessDenied,
    WorkspaceAccessDenied,
    WorkspaceFolderManipulationAccessDenied,
)


class CheckAccessService:
    def __init__(self, session, user_id: uuid.UUID, is_super_admin=False):
        self.session = session
        self.user_id = user_id
        self.is_super_admin = is_super_admin

    async def _check_workspace_roles(
        self,
        owner_id: uuid.UUID,
        roles: list[Role] | None = None,
        *,
        exception=None,
    ):
        if owner_id == self.user_id:
            return

        has_access = await AppletAccessCRUD(self.session).has_any_roles_for_workspace(owner_id, self.user_id, roles)

        if not has_access:
            raise exception or WorkspaceAccessDenied()

    async def _check_applet_roles(
        self,
        applet_id: uuid.UUID,
        roles: list[Role] | None = None,
        *,
        exception=None,
    ):
        has_access = await AppletAccessCRUD(self.session).has_any_roles_for_applet(applet_id, self.user_id, roles)

        if not has_access:
            raise exception or AppletAccessDenied()

    async def check_applet_detail_access(self, applet_id: uuid.UUID):
        await self._check_applet_roles(applet_id)

    async def check_workspace_applet_detail_access(self, applet_id: uuid.UUID):
        await self._check_applet_roles(
            applet_id,
            roles=[
                Role.SUPER_ADMIN,
                Role.OWNER,
                Role.MANAGER,
                Role.COORDINATOR,
                Role.EDITOR,
                Role.REVIEWER,
            ],
        )

    async def check_workspace_access(self, owner_id: uuid.UUID):
        await self._check_workspace_roles(owner_id)

    async def check_workspace_manager_accesses_access(self, owner_id: uuid.UUID):
        await self._check_workspace_roles(owner_id, [Role.OWNER, Role.MANAGER])

    async def check_workspace_manager_list_access(self, owner_id: uuid.UUID):
        await self._check_workspace_roles(owner_id, [Role.OWNER, Role.MANAGER])

    async def check_applet_manager_list_access(self, applet_id: uuid.UUID):
        await self._check_applet_roles(applet_id, [Role.OWNER, Role.MANAGER])

    async def check_workspace_respondent_list_access(self, owner_id: uuid.UUID):
        roles = [Role.OWNER, Role.MANAGER, Role.COORDINATOR, Role.REVIEWER]
        await self._check_workspace_roles(owner_id, roles)

    async def check_applet_respondent_list_access(self, applet_id: uuid.UUID):
        roles = [Role.OWNER, Role.MANAGER, Role.COORDINATOR, Role.REVIEWER]
        await self._check_applet_roles(applet_id, roles)

    async def check_workspace_folder_access(self, owner_id: uuid.UUID):
        await self._check_workspace_roles(
            owner_id,
            Role.managers(),
            exception=WorkspaceFolderManipulationAccessDenied(),
        )

    async def check_applet_create_access(self, owner_id: uuid.UUID):
        if owner_id == self.user_id:
            return
        has_access = await AppletAccessCRUD(self.session).can_create_applet(owner_id, self.user_id)
        if not has_access:
            raise AppletCreationAccessDenied()

    async def check_applet_edit_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_edit_applet(applet_id, self.user_id)

        if not has_access:
            raise AppletEditionAccessDenied()

    async def check_applet_retention_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_set_retention(applet_id, self.user_id)

        if not has_access:
            raise AppletEditionAccessDenied()

    async def check_link_edit_access(self, applet_id: uuid.UUID):
        await self._check_applet_roles(
            applet_id,
            [Role.OWNER, Role.MANAGER, Role.COORDINATOR],
            exception=AppletEditionAccessDenied(),
        )

    async def check_applet_duplicate_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_edit_applet(applet_id, self.user_id)
        if not has_access:
            raise AppletDuplicateAccessDenied()

    async def check_applet_delete_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_edit_applet(applet_id, self.user_id)
        if not has_access:
            raise AppletDeleteAccessDenied()

    async def check_answer_create_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).has_role(applet_id, self.user_id, Role.RESPONDENT)

        if not has_access:
            raise AnswerCreateAccessDenied()

    async def check_answer_review_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_see_data(applet_id, self.user_id)

        if not has_access:
            raise AnswerViewAccessDenied()

    async def check_note_crud_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_see_data(applet_id, self.user_id)

        if not has_access:
            raise AnswerNoteCRUDAccessDenied()

    async def check_applet_invite_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_invite_anyone(applet_id, self.user_id)

        if not has_access:
            raise AppletInviteAccessDenied()

    async def check_applet_schedule_create_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_set_schedule_and_notifications(applet_id, self.user_id)

        if not has_access:
            raise AppletSetScheduleAccessDenied()

    async def check_create_transfer_ownership_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).has_role(applet_id, self.user_id, Role.OWNER)

        if not has_access:
            raise TransferOwnershipAccessDenied()

    async def check_publish_conceal_access(self):
        if not self.is_super_admin:
            raise PublishConcealAccessDenied()

    async def check_answers_export_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).check_export_access(applet_id, self.user_id)

        if not has_access:
            raise AppletAccessDenied()

    async def check_applet_share_library_access(self, applet_id: uuid.UUID):
        await self._check_applet_roles(applet_id, [Role.OWNER])

    async def check_answers_mobile_data_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).has_role(applet_id, self.user_id, Role.RESPONDENT)

        if not has_access:
            raise AppletAccessDenied()

    async def check_answer_check_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).has_role(applet_id, self.user_id, Role.RESPONDENT)

        if not has_access:
            raise AnswerCheckAccessDenied()
