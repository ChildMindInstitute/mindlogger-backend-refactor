import uuid

from asyncpg.exceptions import UniqueViolationError

from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role, UserAppletAccess
from apps.invitations.constants import InvitationStatus
from apps.invitations.crud import InvitationCRUD
from apps.invitations.domain import InvitationDetailGeneric
from apps.shared.exception import NotFoundError
from apps.users import UserNotFound, UsersCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema

__all__ = ["UserAppletAccessService"]

from apps.workspaces.domain.user_applet_access import (
    RespondentInfo,
    RespondentInfoPublic,
)
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

    async def _get_default_role_meta_for_anonymous_respondent(self) -> dict:
        meta: dict = {}
        meta.update(
            secretUserId="Guest Account Submission",
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
        nickname = meta.pop("nickname", None)

        access_schema = await UserAppletAccessCRUD(self.session).save(
            UserAppletAccessSchema(
                user_id=user_id,
                applet_id=self._applet_id,
                role=role,
                owner_id=self._user_id,
                invitor_id=self._user_id,
                meta=meta,
                nickname=nickname,
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
            ).get_applet_role_by_user_id_exist(
                self._applet_id, anonymous_respondent.id, Role.RESPONDENT
            )
            if access_schema:
                if access_schema.is_deleted:
                    await UserAppletAccessCRUD(self.session).restore(
                        "id", access_schema.id
                    )
                return UserAppletAccess.from_orm(access_schema)

            meta = await self._get_default_role_meta_for_anonymous_respondent()
            owner_access = await UserAppletAccessCRUD(
                self.session
            ).get_applet_owner(applet_id=self._applet_id)
            access_schema = await UserAppletAccessCRUD(self.session).save(
                UserAppletAccessSchema(
                    user_id=anonymous_respondent.id,
                    applet_id=self._applet_id,
                    role=Role.RESPONDENT,
                    owner_id=owner_access.user_id,
                    invitor_id=self._user_id,
                    meta=meta,
                    nickname=None,
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
        respondent_nickname = invitation.dict().get("nickname", None)

        if invitation.role in [Role.RESPONDENT, Role.REVIEWER]:
            meta = invitation.meta.dict(by_alias=True)  # type: ignore

        if invitation.role == Role.MANAGER:
            await UserAppletAccessCRUD(self.session).delete_user_roles(
                invitation.applet_id, self._user_id, manager_included_roles
            )

        access_schema = await UserAppletAccessCRUD(
            self.session
        ).upsert_user_applet_access(
            schema=UserAppletAccessSchema(
                user_id=self._user_id,
                applet_id=invitation.applet_id,
                role=invitation.role,
                owner_id=owner_access.user_id,
                invitor_id=invitation.invitor_id,
                meta=meta,
                nickname=respondent_nickname,
                is_deleted=False,
            ),
            where=UserAppletAccessSchema.soft_exists(exists=False),
        )

        if invitation.role != Role.RESPONDENT:
            has_respondent = await UserAppletAccessCRUD(self.session).has_role(
                invitation.applet_id, self._user_id, Role.RESPONDENT
            )
            if not has_respondent:
                meta = await self._get_default_role_meta(
                    Role.RESPONDENT, self._user_id
                )
                nickname = meta.pop("nickname", None)
                schema = UserAppletAccessSchema(
                    user_id=self._user_id,
                    applet_id=invitation.applet_id,
                    role=Role.RESPONDENT,
                    owner_id=owner_access.user_id,
                    invitor_id=invitation.invitor_id,
                    meta=meta,
                    nickname=nickname,
                    is_deleted=False,
                )

                await UserAppletAccessCRUD(
                    self.session
                ).upsert_user_applet_access(schema)

        return UserAppletAccess.from_orm(access_schema[0])

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
        # change here
        access.meta["secretUserId"] = schema.secret_user_id
        await crud.update_meta_by_access_id(
            access.id, access.meta, nickname=schema.nickname
        )

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

    async def get_respondent_info(
        self,
        respondent_id: uuid.UUID,
        applet_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> RespondentInfoPublic:
        crud = UserAppletAccessCRUD(self.session)
        respondent_schema = await crud.get_respondent_by_applet_and_owner(
            respondent_id, applet_id, owner_id
        )
        if not respondent_schema:
            raise NotFoundError()

        if respondent_schema.meta:
            return RespondentInfoPublic(
                nickname=respondent_schema.nickname,
                secret_user_id=respondent_schema.meta.get("secretUserId"),
            )
        else:
            return RespondentInfoPublic(
                nickname=respondent_schema.nickname, secret_user_id=None
            )

    async def has_role(self, role: str) -> bool:
        manager_roles = set(Role.managers())
        is_manager = role in manager_roles
        current_roles = await UserAppletAccessCRUD(
            self.session
        ).get_user_roles_to_applet(self._user_id, self._applet_id)
        if not is_manager:
            return role in current_roles
        else:
            user_roles = set(current_roles)
            return role in manager_roles and bool(
                user_roles.intersection(manager_roles)
            )

    async def get_respondent_access(self) -> UserAppletAccessSchema | None:
        crud = UserAppletAccessCRUD(self.session)
        return await crud.get(
            self._user_id, self._applet_id, Role.RESPONDENT.value
        )

    async def get_owner(self) -> UserAppletAccessSchema:
        crud = UserAppletAccessCRUD(self.session)
        return await crud.get_applet_owner(self._applet_id)
