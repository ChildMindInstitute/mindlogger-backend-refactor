from typing import Any

from sqlalchemy.exc import IntegrityError

from apps.users.db.schemas import UserSchema
from apps.users.domain import (
    User,
    UserChangePassword,
    UserCreate,
    UserUpdateRequest,
)
from apps.users.errors import (
    UserAlreadyExistError,
    UserIsDeletedError,
    UserNotFound,
    UsersError,
)
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

        # TODO: Align with client about the business logic
        if instance.is_deleted:
            raise UserIsDeletedError(
                "This user is deleted. "
                "The recovery logic is not implemented yet."
            )

        # Get internal model
        user = User.from_orm(instance)

        return user

    async def get_by_id(self, id_: int) -> User:
        return await self._fetch(key="id", value=id_)

    async def get_by_email(self, email: str) -> User:
        return await self._fetch(key="email", value=email)

    async def save(self, schema: UserCreate) -> tuple[User, bool]:
        # Save user into the database
        try:
            instance: UserSchema = await self._create(
                self.schema_class(**schema.dict())
            )
        except IntegrityError:
            raise UserAlreadyExistError

        # Create internal data model
        user = User.from_orm(instance)

        return user, True

    async def update(
        self, user: User, update_schema: UserUpdateRequest
    ) -> User:
        # Update user in database
        instance = await self._update_one(
            lookup="id",
            value=user.id,
            schema=UserSchema(full_name=update_schema.full_name),
        )

        # Create internal data model
        user = User.from_orm(instance)

        return user

    async def delete(self, user: User) -> User:
        # Update user in database
        instance = await self._update_one(
            lookup="id", value=user.id, schema=UserSchema(is_deleted=True)
        )

        # Create internal data model
        user = User.from_orm(instance)

        return user

    async def change_password(
        self, user: User, update_schema: UserChangePassword
    ) -> User:
        # Update user in database
        instance = await self._update_one(
            lookup="id",
            value=user.id,
            schema=UserSchema(hashed_password=update_schema.hashed_password),
        )
        return User.from_orm(instance)
