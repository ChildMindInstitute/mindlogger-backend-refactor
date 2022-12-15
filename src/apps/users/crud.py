from typing import Any

from apps.users.db.schemas import UserSchema
from apps.users.domain import User, UserCreate, UserIsDeleted
from apps.users.errors import UserIsDeletedError, UserNotFound, UsersError
from infrastructure.database.crud import BaseCRUD


class UsersCRUD(BaseCRUD[UserSchema]):
    schema_class = UserSchema

    async def _fetch(self, key: str, value: Any) -> User:
        """Fetch user by id or email from the database."""

        if key not in {"id", "email"}:
            raise UsersError(f"Can not make the looking up by {key} {value}")

        # Get user from the database
        if not (instance := await self._get(key, value)):
            raise UserNotFound(
                f"No such user with {key}={value}. \n" f"Are you registered?"
            )

        user_with_flag: UserIsDeleted = UserIsDeleted.from_orm(instance)
        if user_with_flag.is_deleted:
            raise UserIsDeletedError(f"User with {key}={value} is deleted")

        # Get internal model
        user = User.from_orm(instance)

        return user

    async def get_by_id(self, id_: int) -> User:
        return await self._fetch(key="id", value=id_)

    async def get_by_email(self, email: str) -> User:
        return await self._fetch(key="email", value=email)

    async def save(self, schema: UserCreate) -> tuple[User, bool]:
        """Return user instance and the created information."""

        # Save user into the database
        instance: UserSchema = await self._create(UserSchema(**schema.dict()))

        # Create internal data model
        user = User.from_orm(instance)

        return user, True

    async def update(
        self,
        lookup: tuple[str, Any],
        payloads: list[dict[str, Any]],
    ) -> User:
        for payload in payloads:
            await self._update(lookup=lookup, payload=payload)
        user = await self._fetch(key=lookup[0], value=lookup[1])

        return user
