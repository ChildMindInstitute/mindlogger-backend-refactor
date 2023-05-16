import uuid

from apps.users.cruds.user_device import UserDevicesCRUD


class UserDeviceService:
    def __init__(self, session, user_id: uuid.UUID):
        self.session = session
        self.user_id = user_id

    async def add_device(self, device_id: str):
        await UserDevicesCRUD(self.session).add_device(self.user_id, device_id)

    async def remove_device(self, device_id: str):
        await UserDevicesCRUD(self.session).remove_device(
            self.user_id, device_id
        )
