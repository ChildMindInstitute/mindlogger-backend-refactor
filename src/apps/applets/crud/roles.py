from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.applets.db.schemas import UserAppletAccessSchema
from apps.applets.domain.constants import Role
from apps.applets.domain.user_applet_access import (
    UserAppletAccess,
    UserAppletAccessCreate,
)
from apps.applets.errors import UserAppletAccessesNotFound
from infrastructure.database.crud import BaseCRUD

__all__ = ["UserAppletAccessCRUD"]


class UserAppletAccessCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

    async def get_by_id(self, id_: int) -> UserAppletAccess:
        """Fetch UserAppletAccess by id from the database."""

        # Get UserAppletAccess from the database
        if not (instance := await self._get("id", id_)):
            raise UserAppletAccessesNotFound(
                f"No such UserAppletAccess with id={id_}."
            )

        # Get internal model
        user_applet_access: UserAppletAccess = UserAppletAccess.from_orm(
            instance
        )

        return user_applet_access

    async def get_by_user_id(self, user_id_: int) -> list[UserAppletAccess]:
        query: Query = select(self.schema_class).filter(
            self.schema_class.user_id == user_id_
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()

        return [
            UserAppletAccess.from_orm(user_applet_access)
            for user_applet_access in results
        ]

    async def get_by_user_id_role_admin(
        self, user_id_: int
    ) -> list[UserAppletAccess]:
        query: Query = select(self.schema_class).filter(
            self.schema_class.user_id == user_id_
            and self.schema_class.role == Role("admin")
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()

        return [
            UserAppletAccess.from_orm(user_applet_access)
            for user_applet_access in results
        ]

    async def get_by_applet_id(
        self, applet_id_: int
    ) -> list[UserAppletAccess]:
        query: Query = select(self.schema_class).filter(
            self.schema_class.applet_id == applet_id_
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()
        return [
            UserAppletAccess.from_orm(user_applet_access)
            for user_applet_access in results
        ]

    async def get_by_admin_user_and_applet(
        self, user_id: int, applet_id: int
    ) -> list[UserAppletAccessSchema]:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == Role.ADMIN)
        result = await self._execute(query)
        results = result.scalars().all()
        return results

    async def save(self, schema: UserAppletAccessCreate) -> UserAppletAccess:
        """Return UserAppletAccess instance and the created information."""

        # Save UserAppletAccess into the database
        instance: UserAppletAccessSchema = await self._create(
            UserAppletAccessSchema(**schema.dict())
        )

        # Create internal data model
        user_applet_access = UserAppletAccess.from_orm(instance)

        return user_applet_access
