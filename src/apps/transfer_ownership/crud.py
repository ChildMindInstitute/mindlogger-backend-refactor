import uuid

from sqlalchemy import delete

from apps.transfer_ownership.db.schemas import TransferSchema
from apps.transfer_ownership.domain import Transfer
from apps.transfer_ownership.errors import TransferNotFoundError
from infrastructure.database.crud import BaseCRUD

__all__ = ["TransferCRUD"]


class TransferCRUD(BaseCRUD[TransferSchema]):
    schema_class = TransferSchema

    async def create(self, transfer: Transfer) -> TransferSchema:
        schema = await self._create(TransferSchema(**transfer.dict()))
        return schema

    async def get_by_key(self, key: uuid.UUID) -> TransferSchema:
        if not (instance := await self._get(key="key", value=key)):
            raise TransferNotFoundError(key)

        return instance

    async def delete_all_by_applet_id(self, applet_id: int) -> None:
        query = delete(self.schema_class)
        query = query.where(self.schema_class.applet_id == applet_id)
        await self._execute(query)

    async def delete_by_key(self, key: uuid.UUID) -> None:
        query = delete(self.schema_class)
        query = query.where(self.schema_class.key == key)
        await self._execute(query)
