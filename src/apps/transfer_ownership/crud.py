import uuid

from sqlalchemy import select, update

from apps.transfer_ownership.constants import TransferOwnershipStatus
from apps.transfer_ownership.db.schemas import TransferSchema
from apps.transfer_ownership.domain import Transfer
from apps.transfer_ownership.errors import TransferNotFoundError
from infrastructure.database.crud import BaseCRUD

__all__ = ["TransferCRUD"]


class TransferCRUD(BaseCRUD[TransferSchema]):
    schema_class = TransferSchema

    async def create(self, transfer: Transfer) -> TransferSchema:
        return await self._create(TransferSchema(**transfer.dict()))

    async def get_by_key(self, key: uuid.UUID) -> TransferSchema:
        query = select(self.schema_class)
        query = query.where(self.schema_class.key == key)
        query = query.where(self.schema_class.status == TransferOwnershipStatus.PENDING)
        result = await self._execute(query)
        instance = result.scalars().first()
        if not instance:
            raise TransferNotFoundError()

        return instance

    async def decline_all_pending_by_applet_id(self, applet_id: uuid.UUID) -> None:
        query = update(self.schema_class)
        query = query.where(TransferSchema.applet_id == applet_id)
        query = query.where(self.schema_class.status == TransferOwnershipStatus.PENDING)
        query = query.values(status=TransferOwnershipStatus.DECLINED)
        await self._execute(query)

    async def decline_by_key(self, key: uuid.UUID, user_id: uuid.UUID) -> None:
        query = update(self.schema_class)
        query = query.where(self.schema_class.key == key)
        query = query.values(status=TransferOwnershipStatus.DECLINED, to_user_id=user_id)
        await self._execute(query)

    async def approve_by_key(self, key: uuid.UUID, user_id: uuid.UUID) -> None:
        query = update(self.schema_class)
        query = query.where(self.schema_class.key == key)
        query = query.values(status=TransferOwnershipStatus.APPROVED, to_user_id=user_id)
        await self._execute(query)
