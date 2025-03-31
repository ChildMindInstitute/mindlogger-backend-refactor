import datetime
import uuid

from sqlalchemy.dialects.postgresql import insert

from apps.users.db.schemas import UserDeviceSchema
from infrastructure.database.crud import BaseCRUD


class UserDevicesCRUD(BaseCRUD[UserDeviceSchema]):
    schema_class = UserDeviceSchema

    async def get_by_device_id(self, device_id: str) -> UserDeviceSchema | None:
        return await self._get(key="device_id", value=device_id)

    async def add_device(self, user_id: uuid.UUID, device_id: str) -> None:
        await self._delete(user_id=user_id, device_id=device_id)

        await self._create(UserDeviceSchema(user_id=user_id, device_id=device_id))

    async def remove_device(self, user_id: uuid.UUID, device_id: str) -> None:
        await self._delete(user_id=user_id, device_id=device_id)

    async def upsert(self, user_id: uuid.UUID, device_id: str, **data):
        values = dict(user_id=user_id, device_id=device_id, **data)
        stmt = (
            insert(UserDeviceSchema)
            .values(values)
            .on_conflict_do_update(
                constraint=UserDeviceSchema.uq_constraint,
                set_={
                    **values,
                    "updated_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
                },
            )
            .returning(UserDeviceSchema)
        )
        result = await self._execute(stmt)

        row = result.mappings().first()
        model = UserDeviceSchema(**row)

        return model
