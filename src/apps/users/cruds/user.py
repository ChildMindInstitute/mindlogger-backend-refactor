import datetime
import uuid
from typing import Any, Collection, List

from sqlalchemy import false, select, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.shared.hashing import hash_sha224
from apps.users.db.schemas import UserSchema
from apps.users.domain import User, UserChangePassword, UserUpdateRequest
from apps.users.errors import UserAlreadyExistError, UserIsDeletedError, UserNotFound
from infrastructure.database.crud import BaseCRUD


class UsersCRUD(BaseCRUD[UserSchema]):
    schema_class = UserSchema

    async def _fetch(self, key: str, value: Any) -> User:
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
        try:
            instance: UserSchema = await self._create(schema)
        except IntegrityError:
            raise UserAlreadyExistError()

        return instance

    async def update(self, user: User, update_schema: UserUpdateRequest) -> User:
        instance = await self._update_one(
            lookup="id",
            value=user.id,
            schema=UserSchema(**update_schema.dict()),
        )

        # Create internal data model
        user = User.from_orm(instance)

        return user

    async def update_by_id(self, pk: uuid.UUID, update_schema: UserSchema) -> UserSchema:
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=update_schema,
        )

        return instance

    async def update_encrypted_email(self, user: User, encrypted_email: str) -> User:
        instance = await self._update_one(
            lookup="id",
            value=user.id,
            schema=UserSchema(email_encrypted=encrypted_email),
        )
        # Create internal data model
        user = User.from_orm(instance)

        return user

    async def delete(self, user_id: uuid.UUID) -> UserSchema:
        instance = await self._update_one(lookup="id", value=user_id, schema=UserSchema(is_deleted=True))
        return instance

    async def change_password(self, user: User, update_schema: UserChangePassword) -> User:
        instance = await self._update_one(
            lookup="id",
            value=user.id,
            schema=UserSchema(hashed_password=update_schema.hashed_password),
        )
        return User.from_orm(instance)

    async def update_last_seen_by_id(self, id_: uuid.UUID) -> None:
        query = update(UserSchema)
        query = query.where(UserSchema.id == id_)
        query = query.values(last_seen_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None))
        await self._execute(query)

    async def exist_by_id(self, id_: uuid.UUID) -> bool:
        query = select(UserSchema)
        query = query.where(UserSchema.id == id_)
        query = query.where(UserSchema.is_deleted == false())

        db_result = await self._execute(query)

        return db_result.scalars().first() is not None

    async def get_super_admin(self) -> UserSchema | None:
        query: Query = select(UserSchema)
        query = query.where(UserSchema.is_super_admin == true())
        db_result = await self._execute(query)
        return db_result.scalars().one_or_none()

    async def get_anonymous_respondent(self) -> UserSchema | None:
        query: Query = select(UserSchema)
        query = query.where(UserSchema.is_anonymous_respondent == true())
        db_result = await self._execute(query)
        return db_result.scalars().one_or_none()

    async def get_by_ids(self, ids: Collection[uuid.UUID]) -> List[UserSchema]:
        query: Query = select(UserSchema)
        query = query.where(UserSchema.id.in_(ids))
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_user_or_none_by_email(self, email: str) -> UserSchema | None:
        email_hash = hash_sha224(email)
        user = await self._get("email", email_hash)
        return user
