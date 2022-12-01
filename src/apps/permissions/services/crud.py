from typing import Any

from apps.permissions.db import UserAppletAccessSchema, Role
from apps.permissions.domain import UserAppletAccess, UserAppletAccessCreate
from apps.permissions.errors import UserAppletAccessesError
from infrastructure.database.crud import BaseCRUD

__all__ = ["PermissionsCRUD"]


class PermissionsCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

    async def _fetch(self, key: str, value: Any) -> UserAppletAccess:
        """Fetch UserAppletAccess by user_id or applet_id from the database."""

        if key not in {"user_id", "applet_id"}:
            raise UserAppletAccessesError(f"Can not make the looking up by {key} {value}")

        # Get UserAppletAccess from the database
        if not (instance := await self._get(key, value)):
            raise UserAppletAccessesError(
                f"No such UserAppletAccess with {key}={value}."
            )

        # Get internal model
        permission: UserAppletAccess = UserAppletAccess.from_orm(instance)

        return permission

    async def get_by_user_id(self, user_id_: int) -> UserAppletAccess:
        return await self._fetch(key="user_id", value=user_id_)

    async def get_by_applet_id(self, applet_id_: int) -> UserAppletAccess:
        return await self._fetch(key="applet_id", value=applet_id_)

    async def get_by_all(self, user_id_: int, applet_id_: int, role: Role) -> UserAppletAccess:
        return await self._fetch(key="user_id", value=user_id_) # TODO

# TODO
    async def _update(
        self,
        lookup: tuple[str, Any],
        payload: dict[str, Any],
    ) -> None:
        """Updates an existed instance of the model in the related table"""

        query: Query = (
            update(self.schema_class)
            .where(getattr(self.schema_class, lookup[0]) == lookup[1])
            .values(
                **payload,
            )
        )
        await self._execute_commit(query)

    async def save_user_permission(self, schema: UserAppletAccessCreate) -> tuple[UserAppletAccess, bool]:
        """Return UserAppletAccess instance and the created information."""

        # Save user into the database
        instance: UserAppletAccessSchema = await self._create(UserAppletAccessSchema(**schema.dict()))

        # Create internal data model
        permission = UserAppletAccess.from_orm(instance)

        return permission, True
