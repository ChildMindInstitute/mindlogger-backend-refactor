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
        user = User.model_validate(instance)

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
            schema=UserSchema(**update_schema.model_dump()),
        )

        # Create internal data model
        user = User.model_validate(instance)

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
        user = User.model_validate(instance)

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
        return User.model_validate(instance)

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

    async def get_prolific_respondent(self, id_: uuid.UUID) -> UserSchema | None:
        query: Query = select(UserSchema)
        query = query.where(UserSchema.id == id_ and UserSchema.is_prolific_respondent == true())
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

    async def update_mfa_status(self, user_id: uuid.UUID, enabled: bool, secret: str | None = None) -> User:
        """Update MFA status for a user."""
        instance = await self._update_one(
            lookup="id",
            value=user_id,
            schema=UserSchema(mfa_enabled=enabled, mfa_secret=secret),
        )
        return User.model_validate(instance)

    async def update_pending_mfa(
        self, user_id: uuid.UUID, encrypted_secret: str, created_at: datetime.datetime
    ) -> User:
        """
        Update pending MFA fields for a user during setup.

        Args:
            user_id: The user's ID
            encrypted_secret: The encrypted TOTP secret
            created_at: Timestamp when setup was initiated

        Returns:
            User: The updated user object
        """
        instance = await self._update_one(
            lookup="id",
            value=user_id,
            schema=UserSchema(pending_mfa_secret=encrypted_secret, pending_mfa_created_at=created_at),
        )
        return User.model_validate(instance)

    async def clear_pending_mfa(self, user_id: uuid.UUID) -> User:
        """
        Clear pending MFA fields for a user.

        Used when setup is completed, expired, or cancelled.

        Args:
            user_id: The user's ID

        Returns:
            User: The updated user object
        """
        instance = await self._update_one(
            lookup="id",
            value=user_id,
            schema=UserSchema(pending_mfa_secret=None, pending_mfa_created_at=None),
        )
        return User.model_validate(instance)

    async def activate_mfa(self, user_id: uuid.UUID, encrypted_secret: str) -> User:
        """
        Activate MFA for a user after successful TOTP verification.

        This method atomically:
        1. Moves pending_mfa_secret to mfa_secret (permanent storage)
        2. Enables MFA (sets mfa_enabled = True)
        3. Clears pending fields (pending_mfa_secret and pending_mfa_created_at)

        Args:
            user_id: The user's ID
            encrypted_secret: The encrypted TOTP secret from pending_mfa_secret

        Returns:
            User: The updated user object with MFA now active
        """
        # Perform UPDATE without RETURNING first
        query = (
            update(UserSchema)
            .where(UserSchema.id == user_id)
            .values(
                mfa_enabled=True,
                mfa_secret=encrypted_secret,
                pending_mfa_secret=None,
                pending_mfa_created_at=None,
            )
        )
        await self._execute(query)
        await self.session.commit()  # Explicitly commit the transaction

        # Then fetch the updated record
        return await self.get_by_id(user_id)

    async def update_last_totp_time_step(self, user_id: uuid.UUID, time_step: int) -> None:
        """
        Update the last used TOTP time step for replay protection.

        Args:
            user_id: The user's UUID
            time_step: Time step value to store (epoch / 30)
        """
        query = update(UserSchema).where(UserSchema.id == user_id).values(last_totp_time_step=time_step)
        await self._execute(query)

    async def disable_mfa(self, user_id: uuid.UUID, disabled_at: datetime.datetime) -> None:
        """
        Disable MFA for a user and clear all MFA-related fields.

        This method atomically:
        1. Disables MFA (sets mfa_enabled = False)
        2. Clears mfa_secret (permanent TOTP secret)
        3. Clears pending_mfa_secret and pending_mfa_created_at
        4. Clears last_totp_time_step (replay protection counter)
        5. Sets mfa_disabled_at timestamp for audit trail

        Args:
            user_id: The user's UUID
            disabled_at: Timestamp when MFA was disabled
        """
        query = (
            update(UserSchema)
            .where(UserSchema.id == user_id)
            .values(
                mfa_enabled=False,
                mfa_secret=None,
                pending_mfa_secret=None,
                pending_mfa_created_at=None,
                last_totp_time_step=None,
                mfa_disabled_at=disabled_at,
            )
        )
        await self._execute(query)
