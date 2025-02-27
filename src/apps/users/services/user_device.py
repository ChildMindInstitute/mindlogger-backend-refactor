import uuid

from apps.users.cruds.user_device import UserDevicesCRUD
from apps.users.domain import UserDevice, UserDeviceCreate


class UserDeviceService:
    def __init__(self, session, user_id: uuid.UUID) -> None:
        self.session = session
        self.user_id = user_id

    async def get_by_device_id(self, device_id: str) -> UserDevice | None:
        schema = await UserDevicesCRUD(self.session).get_by_device_id(device_id)

        return UserDevice.from_schema(schema) if schema else None

    async def add_device(self, data: UserDeviceCreate) -> UserDevice:
        app_data = dict(
            app_version=data.app_version,
            os_name=data.os.name if data.os else None,
            os_version=data.os.version if data.os else None,
        )
        schema = await UserDevicesCRUD(self.session).upsert(
            self.user_id, data.device_id, **{k: v for k, v in app_data.items() if v is not None}
        )
        return UserDevice.from_schema(schema)

    async def remove_device(self, device_id: str) -> None:
        await UserDevicesCRUD(self.session).remove_device(self.user_id, device_id)
