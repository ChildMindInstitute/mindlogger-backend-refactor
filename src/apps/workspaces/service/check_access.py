import uuid

from apps.workspaces.crud.applet_access import AppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.errors import (
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
    def __init__(self, session, user_id: uuid.UUID):
        self.session = session
        self.user_id = user_id

    async def check_applet_detail_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(
            self.session
        ).has_any_roles_for_applet(applet_id, self.user_id)

        if not has_access:
            raise AppletAccessDenied()

    async def check_workspace_access(self, owner_id: uuid.UUID):
        has_access = await AppletAccessCRUD(
            self.session
        ).has_any_roles_for_workspace(owner_id, self.user_id)

        if not has_access:
            raise WorkspaceAccessDenied()

    async def check_workspace_manager_accesses_access(
        self, owner_id: uuid.UUID
    ):
        has_access = await AppletAccessCRUD(
            self.session
        ).has_any_roles_for_workspace(
            owner_id, self.user_id, [Role.OWNER, Role.MANAGER]
        )

        if not has_access:
            raise WorkspaceAccessDenied()

    async def check_workspace_folder_access(self, owner_id: uuid.UUID):
        has_access = await AppletAccessCRUD(
            self.session
        ).has_any_roles_for_workspace(owner_id, self.user_id, Role.managers())

        if not has_access:
            raise WorkspaceFolderManipulationAccessDenied()

    async def check_applet_create_access(self, owner_id: uuid.UUID):
        if owner_id == self.user_id:
            return
        has_access = await AppletAccessCRUD(self.session).can_create_applet(
            owner_id, self.user_id
        )
        if not has_access:
            raise AppletCreationAccessDenied()

    async def check_applet_edit_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_edit_applet(
            applet_id, self.user_id
        )

        if not has_access:
            raise AppletEditionAccessDenied()

    async def check_applet_retention_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_set_retention(
            applet_id, self.user_id
        )

        if not has_access:
            raise AppletEditionAccessDenied()

    async def check_link_edit_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(
            self.session
        ).has_any_roles_for_applet(
            applet_id,
            self.user_id,
            [Role.OWNER, Role.MANAGER, Role.COORDINATOR],
        )

        if not has_access:
            raise AppletEditionAccessDenied()

    async def check_applet_duplicate_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_edit_applet(
            applet_id, self.user_id
        )
        if not has_access:
            raise AppletDuplicateAccessDenied()

    async def check_applet_delete_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_edit_applet(
            applet_id, self.user_id
        )
        if not has_access:
            raise AppletDeleteAccessDenied()

    async def check_answer_create_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).has_role(
            applet_id, self.user_id, Role.RESPONDENT
        )

        if not has_access:
            raise AnswerCreateAccessDenied()

    async def check_answer_review_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_see_data(
            applet_id, self.user_id
        )

        if not has_access:
            raise AnswerViewAccessDenied()

    async def check_note_crud_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_see_data(
            applet_id, self.user_id
        )

        if not has_access:
            raise AnswerNoteCRUDAccessDenied()

    async def check_applet_invite_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).can_invite_anyone(
            applet_id, self.user_id
        )

        if not has_access:
            raise AppletInviteAccessDenied()

    async def check_applet_schedule_create_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(
            self.session
        ).can_set_schedule_and_notifications(applet_id, self.user_id)

        if not has_access:
            raise AppletSetScheduleAccessDenied()

    async def check_create_transfer_ownership_access(
        self, applet_id: uuid.UUID
    ):
        has_access = await AppletAccessCRUD(self.session).has_role(
            applet_id, self.user_id, Role.OWNER
        )

        if not has_access:
            raise TransferOwnershipAccessDenied()

    async def check_publish_conceal_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).has_role(
            applet_id, self.user_id, Role.OWNER
        )

        if not has_access:
            raise PublishConcealAccessDenied()
