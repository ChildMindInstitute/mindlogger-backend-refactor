import uuid

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Query

from apps.users.db.schemas import UserDeviceSchema
from apps.users.errors import UserDeviceNotFound
from infrastructure.database.crud import BaseCRUD


class UserDevicesCRUD(BaseCRUD[UserDeviceSchema]):
    schema_class = UserDeviceSchema

    async def add_device(self, user_id: uuid.UUID, device_id: str):
        await self._delete("device_id", device_id)

        await self._create(
            UserDeviceSchema(user_id=user_id, device_id=device_id)
        )

    async def remove_device(self, user_id: uuid.UUID, device_id: str):
        query: Query = select(UserDeviceSchema)
        query = query.where(UserDeviceSchema.device_id == device_id)
        query = query.where(UserDeviceSchema.user_id == user_id)
        db_result = await self._execute(query)
        try:
            db_result.scalars().one()
            await self._delete("device_id", device_id)
        except NoResultFound:
            raise UserDeviceNotFound()
