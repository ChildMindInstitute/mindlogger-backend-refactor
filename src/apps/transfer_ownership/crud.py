import uuid

from sqlalchemy import delete, update

from apps.transfer_ownership.db.schemas import TransferSchema
from apps.transfer_ownership.domain import Transfer
from apps.transfer_ownership.errors import TransferNotFoundError
from infrastructure.database.crud import BaseCRUD
from apps.transfer_ownership.constants import TransferOwnershipStatus


__all__ = ["TransferCRUD"]


class TransferCRUD(BaseCRUD[TransferSchema]):
    schema_class = TransferSchema

    async def create(self, transfer: Transfer) -> TransferSchema:
        return await self._create(TransferSchema(**transfer.dict()))

    async def get_by_key(self, key: uuid.UUID) -> TransferSchema:
        if not (instance := await self._get(key="key", value=key)):
            raise TransferNotFoundError()

        return instance

    async def decline_all_pending_by_applet_id(
        self, applet_id: uuid.UUID
    ) -> None:
        query = update(self.schema_class)
        query = query.where(TransferSchema.applet_id == applet_id)
        query = query.where(
            self.schema_class.status == TransferOwnershipStatus.PENDING
        )
        query = query.values(status=TransferOwnershipStatus.DECLINED)
        await self._execute(query)

    async def decline_by_key(self, key: uuid.UUID) -> None:
        query = update(self.schema_class)
        query = query.where(self.schema_class.key == key)
        query = query.values(status=TransferOwnershipStatus.DECLINED)
        await self._execute(query)

    async def approve_by_key(self, key: uuid.UUID) -> None:
        query = update(self.schema_class)
        query = query.where(self.schema_class.key == key)
        query = query.values(status=TransferOwnershipStatus.APPROVED)
        await self._execute(query)
