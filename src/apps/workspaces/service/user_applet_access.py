import uuid

from asyncpg.exceptions import UniqueViolationError

from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role, UserAppletAccess
from apps.invitations.constants import InvitationStatus
from apps.invitations.crud import InvitationCRUD
from apps.invitations.domain import InvitationDetailGeneric
from apps.users import UserNotFound, UsersCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema

__all__ = ["UserAppletAccessService"]

from apps.workspaces.domain.user_applet_access import RespondentInfo
from apps.workspaces.errors import (
    UserAppletAccessNotFound,
    UserSecretIdAlreadyExists,
    UserSecretIdAlreadyExistsInInvitation,
)


class UserAppletAccessService:
    def __init__(self, session, user_id: uuid.UUID, applet_id: uuid.UUID):
        self._user_id = user_id
        self._applet_id = applet_id
        self.session = session

    async def _get_default_role_meta(
        self, role: Role, user_id: uuid.UUID
    ) -> dict:
        meta: dict = {}
        if role == Role.RESPONDENT:
            user = await UsersCRUD(self.session).get_by_id(user_id)
            meta.update(
                secretUserId=str(uuid.uuid4()),
                nickname=f"{user.first_name} {user.last_name}",
            )

        return meta

    async def _get_default_role_meta_for_anonymous_respondent(
        self, user_id: uuid.UUID
    ) -> dict:
        meta: dict = {}

        user = await UsersCRUD(self.session).get_by_id(user_id)
        meta.update(
            secretUserId="Guest Account Submission",
            nickname=f"{user.first_name} {user.last_name}",
        )

        return meta

    async def add_role(
        self, user_id: uuid.UUID, role: Role
    ) -> UserAppletAccess:
        access_schema = await UserAppletAccessCRUD(
            self.session
        ).get_applet_role_by_user_id(self._applet_id, user_id, role)
        if access_schema:
            return UserAppletAccess.from_orm(access_schema)

        meta = await self._get_default_role_meta(role, user_id)

        access_schema = await UserAppletAccessCRUD(self.session).save(
            UserAppletAccessSchema(
                user_id=user_id,
                applet_id=self._applet_id,
                role=role,
                owner_id=self._user_id,
                invitor_id=self._user_id,
                meta=meta,
            )
        )
        return UserAppletAccess.from_orm(access_schema)

    async def add_role_for_anonymous_respondent(
        self,
    ) -> UserAppletAccess | None:
        anonymous_respondent = await UsersCRUD(
            self.session
        ).get_anonymous_respondent()
        if anonymous_respondent:
            access_schema = await UserAppletAccessCRUD(
                self.session
            ).get_applet_role_by_user_id(
                self._applet_id, anonymous_respondent.id, Role.RESPONDENT
            )
            if access_schema:
                return UserAppletAccess.from_orm(access_schema)

            meta = await self._get_default_role_meta_for_anonymous_respondent(
                anonymous_respondent.id,
            )

            access_schema = await UserAppletAccessCRUD(self.session).save(
                UserAppletAccessSchema(
                    user_id=anonymous_respondent.id,
                    applet_id=self._applet_id,
                    role=Role.RESPONDENT,
                    owner_id=self._user_id,
                    invitor_id=self._user_id,
                    meta=meta,
                )
            )
            return UserAppletAccess.from_orm(access_schema)
        else:
            raise UserNotFound

    async def add_role_by_invitation(
        self, invitation: InvitationDetailGeneric
    ):
        assert (
            invitation.role != Role.OWNER
        ), "Admin role can not be added by invitation"

        manager_included_roles = [Role.EDITOR, Role.COORDINATOR, Role.REVIEWER]
        if invitation.role in manager_included_roles:
            if access := await self.get_access(Role.MANAGER):
                # user already has role upper requested one
                return access

        if access := await self.get_access(invitation.role):
            # user already has role
            return access

        owner_access = await UserAppletAccessCRUD(
            self.session
        ).get_applet_owner(invitation.applet_id)
        meta: dict = dict()

        if invitation.role in [Role.RESPONDENT, Role.REVIEWER]:
            meta = invitation.meta.dict(by_alias=True)  # type: ignore

        if invitation.role == Role.MANAGER:
            await UserAppletAccessCRUD(self.session).delete_user_roles(
                invitation.applet_id, self._user_id, manager_included_roles
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

        if invitation.role != Role.RESPONDENT:
            has_respondent = await UserAppletAccessCRUD(self.session).has_role(
                invitation.applet_id, self._user_id, Role.RESPONDENT
            )
            if not has_respondent:
                meta = await self._get_default_role_meta(
                    Role.RESPONDENT, self._user_id
                )
                schema = UserAppletAccessSchema(
                    user_id=self._user_id,
                    applet_id=invitation.applet_id,
                    role=Role.RESPONDENT,
                    owner_id=owner_access.user_id,
                    invitor_id=invitation.invitor_id,
                    meta=meta,
                    is_deleted=False,
                )

                await UserAppletAccessCRUD(
                    self.session
                ).upsert_user_applet_access(schema)

        return UserAppletAccess.from_orm(access_schema)

    async def add_role_by_private_invitation(self, role: Role):
        owner_access = await UserAppletAccessCRUD(
            self.session
        ).get_applet_owner(self._applet_id)

        if role == Role.RESPONDENT:
            meta = dict(
                secretUserId=str(uuid.uuid4()),
            )
        else:
            meta = dict()

        schema = UserAppletAccessSchema(
            user_id=self._user_id,
            applet_id=self._applet_id,
            role=role,
            owner_id=owner_access.user_id,
            invitor_id=owner_access.user_id,
            meta=meta,
            is_deleted=False,
        )

        try:
            await UserAppletAccessCRUD(self.session).upsert_user_applet_access(
                schema,
                where=UserAppletAccessSchema.soft_exists(exists=False),
            )
        except UniqueViolationError:
            pass

    async def get_roles(self) -> list[str]:
        roles = await UserAppletAccessCRUD(
            self.session
        ).get_user_roles_to_applet(self._user_id, self._applet_id)
        return roles

    async def update_meta(
        self, respondent_id: uuid.UUID, role: Role, schema: RespondentInfo
    ):
        crud = UserAppletAccessCRUD(self.session)
        access = await crud.get(respondent_id, self._applet_id, role)
        if not access:
            raise UserAppletAccessNotFound()
        await self._validate_secret_user_id(access.id, schema.secret_user_id)
        for key, val in schema.dict(by_alias=True).items():
            access.meta[key] = val
        await crud.update_meta_by_access_id(access.id, access.meta)

    async def _validate_secret_user_id(
        self, exclude_id: uuid.UUID, secret_id: str
    ):
        access = await UserAppletAccessCRUD(
            self.session
        ).get_by_secret_user_id_for_applet(
            self._applet_id, secret_id, exclude_id
        )
        if access:
            raise UserSecretIdAlreadyExists()
        invitation = await InvitationCRUD(self.session).get_for_respondent(
            self._applet_id, secret_id, InvitationStatus.PENDING
        )
        if invitation:
            raise UserSecretIdAlreadyExistsInInvitation()

    async def get_admins_role(self) -> Role | None:
        """
        Checks whether user is in admin group and returns role

        Permissions:
        - Transfer ownership
        - All permission
        """
        access = await UserAppletAccessCRUD(self.session).get(
            self._user_id, self._applet_id, Role.OWNER
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
            self._user_id, self._applet_id, [Role.OWNER, Role.MANAGER]
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
            [Role.OWNER, Role.MANAGER, Role.COORDINATOR],
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
            [Role.OWNER, Role.MANAGER, Role.EDITOR],
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
            self._user_id, self._applet_id, [Role.OWNER, Role.MANAGER]
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
            [Role.OWNER, Role.MANAGER, Role.REVIEWER],
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
                Role.OWNER,
                Role.MANAGER,
                Role.COORDINATOR,
                Role.EDITOR,
                Role.REVIEWER,
                Role.RESPONDENT,
            ],
        )
        return getattr(access, "role", None)

    async def get_access(self, role: Role) -> UserAppletAccess | None:
        schema = await UserAppletAccessCRUD(self.session).get(
            self._user_id, self._applet_id, role
        )
        if not schema:
            return None

        return UserAppletAccess.from_orm(schema)

    async def get_nickname(self) -> str | None:
        return await UserAppletAccessCRUD(self.session).get_user_nickname(
            self._applet_id, self._user_id
        )
