import datetime
import uuid
from typing import Any, Collection, List

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.shared.hashing import hash_sha224
from apps.users.db.schemas import UserSchema
from apps.users.domain import User, UserChangePassword, UserUpdateRequest
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
            raise UsersError(key=key, value=value)

        # Get user from the database
        if not (instance := await self._get(key, value)):
            raise UserNotFound
        # TODO: Align with client about the business logic
        if instance.is_deleted:
            raise UserIsDeletedError()

        # Get internal model
        user = User.from_orm(instance)

        return user

    async def get_by_id(self, id_: uuid.UUID) -> User:
        return await self._fetch(key="id", value=id_)

    async def get_by_email(self, email: str) -> User:
        email_hash = hash_sha224(email)
        return await self._fetch(key="email", value=email_hash)

    async def save(self, schema: UserSchema) -> UserSchema:
        # Save user into the database
        try:
            instance: UserSchema = await self._create(schema)
        except IntegrityError:
            raise UserAlreadyExistError()

        return instance

    async def update(
        self, user: User, update_schema: UserUpdateRequest
    ) -> User:
        # Update user in database
        instance = await self._update_one(
            lookup="id",
            value=user.id,
            schema=UserSchema(**update_schema.dict()),
        )

        # Create internal data model
        user = User.from_orm(instance)

        return user

    async def update_by_id(
        self, pk: uuid.UUID, update_schema: UserSchema
    ) -> UserSchema:
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=update_schema,
        )

        return instance

    async def update_encrypted_email(
        self, user: User, encrypted_email: bytes
    ) -> User:
        # Update user in database
        instance = await self._update_one(
            lookup="id",
            value=user.id,
            schema=UserSchema(email_aes_encrypted=encrypted_email),
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

    async def update_last_seen_by_id(self, id_: uuid.UUID):
        query = update(UserSchema)
        query = query.where(UserSchema.id == id_)
        query = query.values(last_seen_at=datetime.datetime.now())
        await self._execute(query)

    async def exist_by_id(self, id_: uuid.UUID) -> bool:
        query = select(UserSchema)
        query = query.where(UserSchema.id == id_)
        query = query.where(UserSchema.is_deleted == False)  # noqa: E712

        db_result = await self._execute(query)

        return db_result.scalars().first() is not None

    async def get_super_admin(self) -> UserSchema | None:
        query: Query = select(UserSchema)
        query = query.where(UserSchema.is_super_admin == True)  # noqa: E712
        db_result = await self._execute(query)
        return db_result.scalars().one_or_none()

    async def get_anonymous_respondent(self) -> UserSchema | None:
        query: Query = select(UserSchema)
        query = query.where(
            UserSchema.is_anonymous_respondent == True  # noqa: E712
        )
        db_result = await self._execute(query)
        return db_result.scalars().one_or_none()

    async def get_by_ids(self, ids: Collection[uuid.UUID]) -> List[UserSchema]:
        query: Query = select(UserSchema)
        query.where(UserSchema.id.in_(ids))
        db_result = await self._execute(query)
        return db_result.scalars().all()  # noqa
