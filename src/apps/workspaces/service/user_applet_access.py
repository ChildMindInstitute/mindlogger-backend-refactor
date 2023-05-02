import uuid

from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role, UserAppletAccess
from apps.invitations.domain import InvitationDetailGeneric
from apps.users import User, UsersCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema

__all__ = ["UserAppletAccessService"]

from apps.workspaces.errors import UserAppletAccessesDenied


class UserAppletAccessService:
    def __init__(self, session, user_id: uuid.UUID, applet_id: uuid.UUID):
        self._user_id = user_id
        self._applet_id = applet_id
        self.session = session

    async def add_role(
        self, user_id: uuid.UUID, role: Role
    ) -> UserAppletAccess:
        access_schema = await UserAppletAccessCRUD(
            self.session
        ).get_applet_role_by_user_id(self._applet_id, self._user_id, role)
        if access_schema:
            return UserAppletAccess.from_orm(access_schema)

        access_schema = await UserAppletAccessCRUD(self.session).save(
            UserAppletAccessSchema(
                user_id=user_id,
                applet_id=self._applet_id,
                role=role,
                owner_id=self._user_id,
                invitor_id=self._user_id,
                meta=dict(),
            )
        )
        return UserAppletAccess.from_orm(access_schema)

    async def add_role_by_invitation(
        self, invitation: InvitationDetailGeneric
    ):
        assert (
            invitation.role != Role.ADMIN
        ), "Admin role can not be added by invitation"
        user = await UsersCRUD(self.session).get_by_id(self._user_id)

        owner_access = await UserAppletAccessCRUD(
            self.session
        ).get_applet_owner(invitation.applet_id)
        meta: dict = dict()

        if invitation.role in [Role.RESPONDENT, Role.REVIEWER]:
            meta = invitation.meta.dict(by_alias=True)  # type: ignore

        if invitation.role == Role.MANAGER:
            await UserAppletAccessCRUD(self.session).clean_manager_accesses(
                invitation.applet_id, self._user_id
            )

        access_schema = await UserAppletAccessCRUD(self.session).save(
            UserAppletAccessSchema(
                user_id=self._user_id,
                applet_id=invitation.applet_id,
                role=invitation.role,
                owner_id=owner_access.user_id,
                invitor_id=invitation.invitor_id,
                meta=meta,
            )
        )

        has_respondent = await UserAppletAccessCRUD(self.session).has_role(
            invitation.applet_id, self._user_id, Role.RESPONDENT
        )
        if not has_respondent:
            await UserAppletAccessCRUD(self.session).save(
                UserAppletAccessSchema(
                    user_id=self._user_id,
                    applet_id=invitation.applet_id,
                    role=Role.RESPONDENT,
                    owner_id=owner_access.user_id,
                    invitor_id=invitation.invitor_id,
                    meta=dict(
                        secretUserId=str(uuid.uuid4()),
                        nickname=f"{user.first_name} {user.last_name}",
                    ),
                )
            )
        return UserAppletAccess.from_orm(access_schema)

    async def add_role_by_private_invitation(self, role: Role):
        owner_access = await UserAppletAccessCRUD(
            self.session
        ).get_applet_owner(self._applet_id)
        user: User = await UsersCRUD(self.session).get_by_id(self._user_id)
        access_schema = await UserAppletAccessCRUD(self.session).save(
            UserAppletAccessSchema(
                user_id=self._user_id,
                applet_id=self._applet_id,
                role=role,
                owner_id=owner_access.user_id,
                invitor_id=owner_access.user_id,
                meta=dict(
                    secretUserId=str(uuid.uuid4()),
                    nickname=f"{user.first_name} {user.last_name}",
                ),
            )
        )
        return UserAppletAccess.from_orm(access_schema)

    async def get_roles(self) -> list[str]:
        roles = await UserAppletAccessCRUD(
            self.session
        ).get_user_roles_to_applet(self._user_id, self._applet_id)
        return roles

    async def get_admins_role(self) -> Role | None:
        """
        Checks whether user is in admin group and returns role

        Permissions:
        - Transfer ownership
        - All permission
        """
        access = await UserAppletAccessCRUD(self.session).get(
            self._user_id, self._applet_id, Role.ADMIN
        )
        return getattr(access, "role", None)

    async def get_organizers_role(self) -> Role | None:
        """
        Checks whether user is in organizer group and returns role

        Permissions:
        - Invite new manager/coordinator/editor/reviewer
        - View all managers/coordinators/editors/reviewers
        - Change roles of managers(for admin)/coordinators/editors/reviewers
        - Delete applet
        """
        access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self._user_id, self._applet_id, [Role.ADMIN, Role.MANAGER]
        )
        return getattr(access, "role", None)

    async def get_respondent_managers_role(self) -> Role | None:
        """
        Checks whether user is in respondents manager group and returns role

        Permissions:
        - Invite new respondent
        - View all respondents
        - Remove specific respondent access
        - Invite new reviewer to specific respondent
        - Set schedule/notifications for respondents
        """
        access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self._user_id,
            self._applet_id,
            [Role.ADMIN, Role.MANAGER, Role.COORDINATOR],
        )
        return getattr(access, "role", None)

    async def get_editors_role(self) -> Role | None:
        """
        Checks whether user is in editor group and returns role

        Permissions:
        - Create applets
        - Update applets
        - Can view all applets
        # TODO: which applets, assigned or all applets in organization
        """
        access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self._user_id,
            self._applet_id,
            [Role.ADMIN, Role.MANAGER, Role.EDITOR],
        )
        return getattr(access, "role", None)

    async def get_reviewers_role(self):
        """
        Checks whether user is in reviewer group and returns role

        Permissions:
        - View/Export all respondents' data
        - Delete specific respondents' data
        """
        access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self._user_id, self._applet_id, [Role.ADMIN, Role.MANAGER]
        )
        return getattr(access, "role", None)

    async def get_reviewer_for_respondent_role(self):
        """
        Checks whether user is in reviewer for
          respondent group and returns role

        Permissions:
        - View assigned respondents' data
        - Export assigned respondents' data
        """
        access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self._user_id,
            self._applet_id,
            [Role.ADMIN, Role.MANAGER, Role.REVIEWER],
        )
        return getattr(access, "role", None)

    async def get_respondents_role(self):
        """
        Checks whether user is in respondent group and returns role

        Permissions:
        - Answer to applet
        """
        access = await UserAppletAccessCRUD(self.session).get_by_roles(
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

    async def get_access(self, role: Role) -> UserAppletAccess:
        schema = await UserAppletAccessCRUD(self.session).get(
            self._user_id, self._applet_id, role
        )
        if not schema:
            raise UserAppletAccessesDenied()

        return UserAppletAccess.from_orm(schema)
