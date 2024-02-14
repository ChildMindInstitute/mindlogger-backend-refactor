from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.cruds.user_device import UserDevicesCRUD
from apps.users.db.schemas import UserDeviceSchema
from apps.users.domain import User
from apps.users.services.user_device import UserDeviceService


@pytest.fixture(scope="session", autouse=True)
async def device_tom(tom: User, global_session: AsyncSession):
    service = UserDeviceService(global_session, tom.id)
    await service.add_device("deviceid")
    await global_session.commit()
    crud = UserDevicesCRUD(global_session)
    device = await crud._get("device_id", "deviceid")
    device = cast(UserDeviceSchema, device)
    yield device.device_id
    await service.remove_device("deviceid")
    await global_session.commit()
