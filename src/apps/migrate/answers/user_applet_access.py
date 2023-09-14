from apps.migrate.answers.crud import MigrateUsersMCRUD
from apps.users import UserNotFound
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.user_applet_access import UserAppletAccess
from apps.workspaces.service.user_applet_access import UserAppletAccessService


class MigrateUserAppletAccessService(UserAppletAccessService):
    async def add_role_for_legacy_deleted_respondent(
        self,
    ) -> UserAppletAccess | None:
        legacy_deleted_respondent = await MigrateUsersMCRUD(
            self.session
        ).get_legacy_deleted_respondent()
        if legacy_deleted_respondent:
            access_schema = await UserAppletAccessCRUD(
                self.session
            ).get_applet_role_by_user_id(
                self._applet_id, legacy_deleted_respondent.id, Role.RESPONDENT
            )
            if access_schema:
                return UserAppletAccess.from_orm(access_schema)

            meta = (
                await self._get_default_role_meta_for_legacy_deleted_respondent()
            )

            crud = UserAppletAccessCRUD(self.session)

            access_schema = await crud.get(
                legacy_deleted_respondent.id,
                self._applet_id,
                Role.RESPONDENT.value,
            )

            if not access_schema:
                access_schema = await UserAppletAccessCRUD(self.session).save(
                    UserAppletAccessSchema(
                        user_id=legacy_deleted_respondent.id,
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

    async def _get_default_role_meta_for_legacy_deleted_respondent(
        self,
    ) -> dict:
        meta: dict = {}

        meta.update(
            secretUserId="Legacy_Deleted_Users",
            nickname=f"Legacy_Deleted_Users",
        )

        return meta
