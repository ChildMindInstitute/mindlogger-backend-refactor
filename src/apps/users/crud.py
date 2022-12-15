from typing import Any

from apps.users.db.schemas import UserSchema
from apps.users.domain import User, UserCreate, UserUpdate
from apps.users.errors import UserNotFound, UsersError
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

        # Get internal model
        user: User = User.from_orm(instance)

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

    # async def update(self, schema: UserUpdate) -> User:
    #     return await self._update(key="email", value=email)

    async def update(
        self,
        id_: int,
        payloads: list[dict[str, Any]],
    ) -> User:
        await self._fetch(key="id", value=id_)
        for payload in payloads:
            await self._update(
                lookup=("id", id_), payload=payload
            )
        user = await self._fetch(key="id", value=id_)

        return user
