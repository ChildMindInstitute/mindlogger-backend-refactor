from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.db.schemas import UserAppletAccessSchema
from apps.applets.domain import Role, UserAppletAccess

__all__ = ["UserAppletAccessService"]


class UserAppletAccessService:
    def __init__(self, user_id: int, applet_id: int):
        self._user_id = user_id
        self._applet_id = applet_id

    async def add_role(self, role: Role) -> UserAppletAccess:
        access_schema = await UserAppletAccessCRUD().get(
            self._user_id, self._applet_id, role
        )
        if not access_schema:
            access_schema = await UserAppletAccessCRUD().save(
                UserAppletAccessSchema(
                    user_id=self._user_id, applet_id=self._applet_id, role=role
                )
            )
        return UserAppletAccess(
            id=access_schema.id,
            user_id=access_schema.user_id,
            applet_id=access_schema.applet_id,
            role=access_schema.role,
        )

    async def is_admin(self) -> Role | None:
        """
        Checks whether user is in admin group and returns role

        Permissions:
        - Transfer ownership
        - All permission
        """
        access = await UserAppletAccessCRUD().get(
            self._user_id, self._applet_id, Role.ADMIN
        )
        return getattr(access, "role", None)

    async def is_organizer(self) -> Role | None:
        """
        Checks whether user is in organizer group and returns role

        Permissions:
        - Invite new manager/coordinator/editor/reviewer
        - View all managers/coordinators/editors/reviewers
        - Change roles of managers(for admin)/coordinators/editors/reviewers
        """
        access = await UserAppletAccessCRUD().get_by_roles(
            self._user_id, self._applet_id, [Role.ADMIN, Role.MANAGER]
        )
        return getattr(access, "role", None)

    async def is_respondents_manager(self) -> Role | None:
        """
        Checks whether user is in respondents manager group and returns role

        Permissions:
        - Invite new respondent
        - View all respondents
        - Remove specific respondent access
        - Invite new reviewer to specific respondent
        - Set schedule/notifications for respondents
        """
        access = await UserAppletAccessCRUD().get_by_roles(
            self._user_id,
            self._applet_id,
            [Role.ADMIN, Role.MANAGER, Role.COORDINATOR],
        )
        return getattr(access, "role", None)

    async def is_editor(self) -> Role | None:
        """
        Checks whether user is in editor group and returns role

        Permissions:
        - Create applets
        - Update applets
        - Can view all applets
        # TODO: which applets, assigned or all applets in organization
        """
        access = await UserAppletAccessCRUD().get_by_roles(
            self._user_id,
            self._applet_id,
            [Role.ADMIN, Role.MANAGER, Role.EDITOR],
        )
        return getattr(access, "role", None)

    async def is_reviewer(self):
        """
        Checks whether user is in reviewer group and returns role

        Permissions:
        - View/Export all respondents' data
        - Delete specific respondents' data
        """
        access = await UserAppletAccessCRUD().get_by_roles(
            self._user_id, self._applet_id, [Role.ADMIN, Role.MANAGER]
        )
        return getattr(access, "role", None)

    async def is_reviewer_for_respondent(self):
        """
        Checks whether user is in reviewer for respondent group and returns role

        Permissions:
        - View assigned respondents' data
        - Export assigned respondents' data
        """
        access = await UserAppletAccessCRUD().get_by_roles(
            self._user_id,
            self._applet_id,
            [Role.ADMIN, Role.MANAGER, Role.REVIEWER],
        )
        return getattr(access, "role", None)

    async def is_respondent(self):
        """
        Checks whether user is in respondent group and returns role

        Permissions:
        - Answer to applet
        """
        access = await UserAppletAccessCRUD().get_by_roles(
            self._user_id,
            self._applet_id,
            [
                Role.ADMIN,
                Role.MANAGER,
                Role.COORDINATOR,
                Role.EDITOR,
                Role.REVIEWER,
                Role.RESPONDENT,
            ],
        )
        return getattr(access, "role", None)
