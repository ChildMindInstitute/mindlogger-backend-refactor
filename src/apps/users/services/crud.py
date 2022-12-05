from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.users.domain import (
    User,
    UserAppletAccess,
    UserAppletAccessCreate,
    UserCreate,
)
from apps.users.errors import (
    UserAppletAccessesNotFound,
    UserNotFound,
    UsersError,
)
from apps.users.db.schemas import UserSchema, Role, UserAppletAccessSchema
from apps.users.domain import User, UserCreate
from apps.users.errors import UserNotFound, UsersError
from infrastructure.database.crud import BaseCRUD

__all__ = [
    "UsersCRUD",
    "PermissionsCRUD",
]


class UsersCRUD(BaseCRUD[UserSchema]):
    schema_class = UserSchema  # type: ignore[assignment]

    async def _fetch(self, key: str, value: Any) -> User:
        """Fetch user by id or email from the database."""

        if key not in {"id", "email"}:
            raise UsersError(f"Can not make the looking up by {key} {value}")

        # Get user from the database
        if not (instance := await self._get(key, value)):
            raise UserNotFound(
                f"No such user with {key}={value}. \n" f"Are you registered?"
            )

        # Get internal model
        user: User = User.from_orm(instance)

        return user

    async def get_by_id(self, id_: int) -> User:
        return await self._fetch(key="id", value=id_)

    async def get_by_email(self, email: str) -> User:
        return await self._fetch(key="email", value=email)

    async def save_user(self, schema: UserCreate) -> tuple[User, bool]:
        """Return user instance and the created information."""

        # Save user into the database
        instance: UserSchema = await self._create(UserSchema(**schema.dict()))

        # Create internal data model
        user = User.from_orm(instance)

        return user, True


class PermissionsCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

    async def get_by_id(self, id_: int) -> UserAppletAccess:
        """Fetch UserAppletAccess by id from the database."""

        # Get UserAppletAccess from the database
        if not (instance := await self._get("id", id_)):
            raise UserAppletAccessesNotFound(
                f"No such UserAppletAccess with id={id_}."
            )

        # Get internal model
        permission: UserAppletAccess = UserAppletAccess.from_orm(instance)

        return permission

    async def get_by_user_id(self, user_id_: int) -> list[UserAppletAccess]:
        query: Query = select(self.schema_class).filter(
            self.schema_class.user_id == user_id_
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()

        return [
            UserAppletAccess.from_orm(permission) for permission in results
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
            UserAppletAccess.from_orm(permission) for permission in results
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
            UserAppletAccess.from_orm(permission) for permission in results
        ]

    async def update_role(self, id_: int, role: Role) -> None:
        await self._update(lookup=("id", id_), payload={"role": role})

    async def save_user_permission(
        self, schema: UserAppletAccessCreate
    ) -> tuple[UserAppletAccess, bool]:
        """Return UserAppletAccess instance and the created information."""

        # Save UserAppletAccess into the database
        instance: UserAppletAccessSchema = await self._create(
            UserAppletAccessSchema(**schema.dict())
        )

        # Create internal data model
        permission = UserAppletAccess.from_orm(instance)

        return permission, True
