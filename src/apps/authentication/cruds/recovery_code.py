import datetime
import uuid

from sqlalchemy import select, update

from apps.authentication.db.schemas import RecoveryCodeSchema
from apps.authentication.domain.recovery_code import RecoveryCode, RecoveryCodeCreate
from infrastructure.database.crud import BaseCRUD


class RecoveryCodeCRUD(BaseCRUD[RecoveryCodeSchema]):
    schema_class = RecoveryCodeSchema

    async def create(self, recovery_code: RecoveryCodeCreate) -> RecoveryCode:
        """Create a new recovery code."""
        instance = await self._create(
            RecoveryCodeSchema(
                user_id=recovery_code.user_id,
                code_hash=recovery_code.code_hash,
                code_encrypted=recovery_code.code_encrypted,
                used=recovery_code.used,
                used_at=recovery_code.used_at,
            )
        )
        return RecoveryCode.model_validate(instance)

    async def create_many(self, recovery_codes: list[RecoveryCodeCreate]) -> list[RecoveryCode]:
        """Create multiple recovery codes in batch."""
        schemas = [
            RecoveryCodeSchema(
                user_id=code.user_id,
                code_hash=code.code_hash,
                code_encrypted=code.code_encrypted,
                used=code.used,
                used_at=code.used_at,
            )
            for code in recovery_codes
        ]
        instances = await self._create_many(schemas)
        return [RecoveryCode.model_validate(instance) for instance in instances]

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[RecoveryCode]:
        """Get all recovery codes for a user."""
        query = select(RecoveryCodeSchema)
        query = query.where(RecoveryCodeSchema.user_id == user_id)
        query = query.where(RecoveryCodeSchema.is_deleted.isnot(True))
        db_result = await self._execute(query)
        instances = db_result.scalars().all()
        return [RecoveryCode.model_validate(instance) for instance in instances]

    async def get_unused_by_user_id(self, user_id: uuid.UUID) -> list[RecoveryCode]:
        """Get all unused recovery codes for a user."""
        query = select(RecoveryCodeSchema)
        query = query.where(RecoveryCodeSchema.user_id == user_id)
        query = query.where(RecoveryCodeSchema.used.is_(False))
        query = query.where(RecoveryCodeSchema.is_deleted.isnot(True))
        db_result = await self._execute(query)
        instances = db_result.scalars().all()
        return [RecoveryCode.model_validate(instance) for instance in instances]

    async def mark_as_used(self, code_id: uuid.UUID) -> RecoveryCode:
        """Mark a recovery code as used."""
        instance = await self._update_one(
            lookup="id",
            value=code_id,
            schema=RecoveryCodeSchema(
                used=True,
                used_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            ),
        )
        return RecoveryCode.model_validate(instance)

    async def delete_by_user_id(self, user_id: uuid.UUID) -> None:
        """Soft delete all recovery codes for a user."""
        query = update(RecoveryCodeSchema)
        query = query.where(RecoveryCodeSchema.user_id == user_id)
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def get_by_id(self, code_id: uuid.UUID) -> RecoveryCode | None:
        """Get a recovery code by ID."""
        instance = await self._get("id", code_id)
        if instance and not instance.is_deleted:
            return RecoveryCode.model_validate(instance)
        return None
