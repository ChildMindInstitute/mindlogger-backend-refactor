from sqlalchemy import distinct, select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.user_applet_access import (
    UserAppletAccess,
    UserAppletAccessItem,
)
from apps.workspaces.errors import UserAppletAccessesNotFound
from infrastructure.database.crud import BaseCRUD

__all__ = ["UserAppletAccessCRUD"]


class UserAppletAccessCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

    async def get_by_id(self, id_: int) -> UserAppletAccess:
        """Fetch UserAppletAccess by id from the database."""

        # Get UserAppletAccess from the database
        if not (instance := await self._get("id", id_)):
            raise UserAppletAccessesNotFound(id_=id_)

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
            self.schema_class.user_id == user_id_,
            self.schema_class.role == Role("admin"),
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()

        return [
            UserAppletAccess.from_orm(user_applet_access)
            for user_applet_access in results
        ]

    async def get_by_applet_id_role_admin(
        self, applet_id_: int
    ) -> UserAppletAccess | None:
        query: Query = select(self.schema_class).filter(
            self.schema_class.applet_id == applet_id_,
            self.schema_class.role == Role.ADMIN,
        )
        result: Result = await self._execute(query)

        return result.scalars().one_or_none()

    async def get_by_user_applet_role(
        self,
        schema: UserAppletAccessItem,
    ) -> UserAppletAccess | None:
        query: Query = select(self.schema_class).filter(
            self.schema_class.user_id == schema.user_id,
            self.schema_class.applet_id == schema.applet_id,
            self.schema_class.role == schema.role,
        )
        result: Result = await self._execute(query)

        return result.scalars().one_or_none()

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

    async def save(
        self, schema: UserAppletAccessSchema
    ) -> UserAppletAccessSchema:
        """Return UserAppletAccess instance and the created information."""
        return await self._create(schema)

    async def get(
        self, user_id: int, applet_id: int, role: str
    ) -> UserAppletAccessSchema | None:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == role)

        result = await self._execute(query)
        return result.scalars().one_or_none()

    async def get_by_roles(
        self, user_id: int, applet_id: int, roles: list[str]
    ) -> UserAppletAccessSchema | None:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))

        result = await self._execute(query)
        return result.scalars().one_or_none()

    # Get by applet id and user id and role respondent
    async def get_by_applet_and_user_as_respondent(
        self, applet_id: int, user_id: int
    ) -> UserAppletAccessSchema:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        result = await self._execute(query)
        return result.scalars().first()

    async def get_user_roles_to_applet(
        self, user_id: int, applet_id
    ) -> list[str]:
        query: Query = select(distinct(UserAppletAccessSchema.role))
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_meta_applet_and_role(
        self, applet_id: int, role: Role
    ) -> list[str]:
        query: Query = select(distinct(UserAppletAccessSchema.meta))
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == role)
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_user_id_applet_and_role(
        self, applet_id: int, role: Role
    ) -> list[str]:
        query: Query = select(distinct(UserAppletAccessSchema.user_id))
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == role)
        db_result = await self._execute(query)

        return db_result.scalars().all()
