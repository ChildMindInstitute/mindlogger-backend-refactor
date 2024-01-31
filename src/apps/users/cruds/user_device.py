import uuid

from apps.users.db.schemas import UserDeviceSchema
from infrastructure.database.crud import BaseCRUD


class UserDevicesCRUD(BaseCRUD[UserDeviceSchema]):
    schema_class = UserDeviceSchema

    async def add_device(self, user_id: uuid.UUID, device_id: str) -> None:
        await self._delete(user_id=user_id, device_id=device_id)

        await self._create(
            UserDeviceSchema(user_id=user_id, device_id=device_id)
        )

    async def remove_device(self, user_id: uuid.UUID, device_id: str) -> None:
        await self._delete(user_id=user_id, device_id=device_id)
