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
)


class CheckAccessService:
    def __init__(self, session, user_id: uuid.UUID):
        self.session = session
        self.user_id = user_id

    async def check_applet_detail_access(self, applet_id: uuid.UUID):
        has_access = await AppletAccessCRUD(self.session).has_any_roles(
            applet_id, self.user_id
        )

        if not has_access:
            raise AppletAccessDenied()

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
